"""SQLite-vec backend implementation."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseVectorStore, Document, SearchResult

logger = logging.getLogger(__name__)


class SqliteVecStore(BaseVectorStore):
    """SQLite-vec 벡터 스토어 백엔드."""

    def _validate_config(self) -> None:
        """설정을 검증합니다."""
        if "db_path" not in self.config:
            # 기본 경로 설정
            self.config["db_path"] = Path.home() / ".pyhub" / "vector.db"
        else:
            self.config["db_path"] = Path(self.config["db_path"]).expanduser()

        # 디렉토리 생성
        self.config["db_path"].parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결을 반환합니다."""
        conn = sqlite3.connect(str(self.config["db_path"]))

        # sqlite-vec 확장 로드
        try:
            conn.enable_load_extension(True)
            try:
                # 일반적인 위치 시도
                conn.load_extension("vec")
            except sqlite3.OperationalError:
                # 플랫폼별 경로 시도
                import platform

                system = platform.system()

                if system == "Darwin":  # macOS
                    paths = [
                        "/opt/homebrew/lib/vec.dylib",
                        "/usr/local/lib/vec.dylib",
                    ]
                elif system == "Linux":
                    paths = [
                        "/usr/lib/x86_64-linux-gnu/vec.so",
                        "/usr/local/lib/vec.so",
                    ]
                else:  # Windows
                    paths = [
                        "vec.dll",
                        r"C:\sqlite\vec.dll",
                    ]

                loaded = False
                for path in paths:
                    try:
                        conn.load_extension(path)
                        loaded = True
                        break
                    except sqlite3.OperationalError:
                        continue

                if not loaded:
                    raise ImportError("sqlite-vec extension not found. " "Install with: pip install sqlite-vec")

        except Exception as e:
            conn.close()
            raise e

        return conn

    def is_available(self) -> bool:
        """백엔드가 사용 가능한지 확인합니다."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # vec_version() 함수 확인
            cursor.execute("SELECT vec_version()")
            version = cursor.fetchone()

            cursor.close()
            conn.close()

            return version is not None

        except Exception as e:
            logger.debug(f"sqlite-vec not available: {e}")
            return False

    def create_collection(self, name: str, dimension: int, distance_metric: str = "cosine", **kwargs) -> None:
        """벡터 컬렉션(테이블)을 생성합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 테이블 생성
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_content TEXT NOT NULL,
                metadata TEXT,
                embedding FLOAT32[{dimension}]
            )
            """
            cursor.execute(create_sql)

            # 벡터 인덱스 생성 (sqlite-vec는 자동으로 처리)
            conn.commit()

        finally:
            cursor.close()
            conn.close()

    def drop_collection(self, name: str) -> None:
        """컬렉션을 삭제합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(f"DROP TABLE IF EXISTS {name}")
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def collection_exists(self, name: str) -> bool:
        """컬렉션이 존재하는지 확인합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
            return cursor.fetchone() is not None
        finally:
            cursor.close()
            conn.close()

    def insert(self, collection_name: str, documents: List[Document], batch_size: int = 1000) -> int:
        """문서들을 컬렉션에 삽입합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            data = [
                (doc.page_content, json.dumps(doc.metadata), json.dumps(doc.embedding))  # sqlite-vec는 JSON 형태로 저장
                for doc in documents
            ]

            cursor.executemany(
                f"""
                INSERT INTO {collection_name} (page_content, metadata, embedding)
                VALUES (?, ?, vec_f32(?))
                """,
                data,
            )

            conn.commit()
            return len(documents)

        finally:
            cursor.close()
            conn.close()

    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """유사도 검색을 수행합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 거리 함수 매핑
        distance_metric = self.config.get("distance_metric", "cosine")
        distance_funcs = {
            "cosine": "vec_distance_cosine",
            "l2": "vec_distance_L2",
        }
        distance_func = distance_funcs.get(distance_metric, "vec_distance_cosine")

        try:
            # 기본 검색 쿼리
            query_vec_json = json.dumps(query_embedding)

            # 거리를 유사도로 변환 (1 - distance)
            search_sql = f"""
            SELECT 
                page_content,
                metadata,
                1 - {distance_func}(embedding, vec_f32(?)) as similarity
            FROM {collection_name}
            WHERE 1 = 1
            """

            params = [query_vec_json]

            # 메타데이터 필터 추가
            if filter:
                for key, value in filter.items():
                    search_sql += f" AND json_extract(metadata, '$.{key}') = ?"
                    params.append(json.dumps(value))

            # 임계값 조건 추가
            if threshold is not None:
                search_sql += f" AND 1 - {distance_func}(embedding, vec_f32(?)) >= ?"
                params.extend([query_vec_json, threshold])

            search_sql += f"""
            ORDER BY {distance_func}(embedding, vec_f32(?))
            LIMIT ?
            """
            params.extend([query_vec_json, k])

            cursor.execute(search_sql, params)
            results = []

            for content, metadata_str, similarity in cursor.fetchall():
                metadata = json.loads(metadata_str) if metadata_str else {}
                doc = Document(page_content=content, metadata=metadata)
                results.append(SearchResult(document=doc, score=similarity))

            return results

        finally:
            cursor.close()
            conn.close()

    def delete(self, collection_name: str, filter: Dict[str, Any]) -> int:
        """필터에 매칭되는 문서들을 삭제합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if not filter:
                # 모든 문서 삭제
                cursor.execute(f"DELETE FROM {collection_name}")
            else:
                # 메타데이터 필터로 삭제
                conditions = []
                params = []

                for key, value in filter.items():
                    conditions.append(f"json_extract(metadata, '$.{key}') = ?")
                    params.append(json.dumps(value))

                where_clause = " AND ".join(conditions)
                cursor.execute(f"DELETE FROM {collection_name} WHERE {where_clause}", params)

            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count

        finally:
            cursor.close()
            conn.close()

    def count(self, collection_name: str) -> int:
        """컬렉션의 문서 수를 반환합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(f"SELECT COUNT(*) FROM {collection_name}")
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            conn.close()

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """컬렉션 정보를 반환합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            info = {"name": collection_name, "backend": self.backend_name, "db_path": str(self.config["db_path"])}

            # 문서 수
            cursor.execute(f"SELECT COUNT(*) FROM {collection_name}")
            info["count"] = cursor.fetchone()[0]

            # 벡터 차원 (스키마에서 추출)
            cursor.execute(f"PRAGMA table_info({collection_name})")
            columns = cursor.fetchall()

            for col in columns:
                if col[1] == "embedding":  # column name
                    # FLOAT32[1536] 형태에서 차원 추출
                    col_type = col[2]
                    if "[" in col_type and "]" in col_type:
                        dim_str = col_type[col_type.index("[") + 1 : col_type.index("]")]
                        info["dimension"] = int(dim_str)
                    break

            # 파일 크기
            import os

            if self.config["db_path"].exists():
                size_bytes = os.path.getsize(self.config["db_path"])
                # 크기를 사람이 읽기 쉬운 형태로 변환
                for unit in ["B", "KB", "MB", "GB"]:
                    if size_bytes < 1024.0:
                        info["size"] = f"{size_bytes:.1f} {unit}"
                        break
                    size_bytes /= 1024.0
                else:
                    info["size"] = f"{size_bytes:.1f} TB"

            return info

        finally:
            cursor.close()
            conn.close()

    @property
    def backend_name(self) -> str:
        """백엔드 이름을 반환합니다."""
        return "sqlite-vec"

    @property
    def required_dependencies(self) -> List[str]:
        """필요한 의존성 패키지 목록을 반환합니다."""
        return ["sqlite-vec"]
