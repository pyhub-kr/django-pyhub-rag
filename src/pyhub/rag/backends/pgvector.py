"""PostgreSQL pgvector backend implementation."""

import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseVectorStore, Document, SearchResult

logger = logging.getLogger(__name__)


class PgVectorStore(BaseVectorStore):
    """PostgreSQL pgvector 벡터 스토어 백엔드."""

    def _validate_config(self) -> None:
        """설정을 검증합니다."""
        if "database_url" not in self.config:
            # Django 설정에서 가져오기 시도
            self._try_django_config()

        if "database_url" not in self.config:
            raise ValueError("database_url is required for pgvector backend")

    def _try_django_config(self) -> None:
        """Django 설정에서 PostgreSQL 데이터베이스 찾기."""
        try:
            from django.conf import settings

            for alias, config in settings.DATABASES.items():
                if "postgresql" in config.get("ENGINE", ""):
                    self.config["database_url"] = self._build_database_url(config)
                    logger.debug(f"Using Django database '{alias}'")
                    return
        except Exception:
            pass

    def _build_database_url(self, config: dict) -> str:
        """Django 데이터베이스 설정을 URL로 변환."""
        user = config.get("USER", "")
        password = config.get("PASSWORD", "")
        host = config.get("HOST", "localhost")
        port = config.get("PORT", "5432")
        dbname = config.get("NAME", "")

        auth = f"{user}:{password}@" if user else ""
        return f"postgresql://{auth}{host}:{port}/{dbname}"

    def _get_connection(self):
        """데이터베이스 연결을 반환합니다."""
        try:
            import psycopg2
        except ImportError:
            raise ImportError("psycopg2 is required for pgvector backend. Install with: pip install psycopg2-binary")

        return psycopg2.connect(self.config["database_url"])

    def is_available(self) -> bool:
        """백엔드가 사용 가능한지 확인합니다."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # pgvector 확장 확인
            cursor.execute("SELECT installed_version FROM pg_available_extensions WHERE name = 'vector'")
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            return result is not None and result[0] is not None

        except Exception as e:
            logger.debug(f"pgvector not available: {e}")
            return False

    def create_collection(
        self, name: str, dimension: int, distance_metric: str = "cosine", index_type: str = "hnsw", **kwargs
    ) -> None:
        """벡터 컬렉션(테이블)을 생성합니다."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 거리 함수 매핑
        distance_ops = {"cosine": "vector_cosine_ops", "l2": "vector_l2_ops", "inner_product": "vector_ip_ops"}

        if distance_metric not in distance_ops:
            raise ValueError(f"Invalid distance metric: {distance_metric}")

        try:
            # 테이블 생성
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {name} (
                id SERIAL PRIMARY KEY,
                page_content TEXT NOT NULL,
                metadata JSONB,
                embedding vector({dimension})
            )
            """
            cursor.execute(create_sql)

            # 인덱스 생성
            if index_type == "hnsw":
                index_sql = f"""
                CREATE INDEX IF NOT EXISTS {name}_embedding_idx 
                ON {name} 
                USING hnsw (embedding {distance_ops[distance_metric]})
                """
            else:  # ivfflat
                lists = kwargs.get("lists", 100)
                index_sql = f"""
                CREATE INDEX IF NOT EXISTS {name}_embedding_idx 
                ON {name} 
                USING ivfflat (embedding {distance_ops[distance_metric]})
                WITH (lists = {lists})
                """

            cursor.execute(index_sql)
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
            cursor.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)", (name,))
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            conn.close()

    def insert(self, collection_name: str, documents: List[Document], batch_size: int = 1000) -> int:
        """문서들을 컬렉션에 삽입합니다."""
        import psycopg2.extras

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            data = [(doc.page_content, json.dumps(doc.metadata), doc.embedding) for doc in documents]

            psycopg2.extras.execute_batch(
                cursor,
                f"""
                INSERT INTO {collection_name} (page_content, metadata, embedding)
                VALUES (%s, %s::jsonb, %s::vector)
                """,
                data,
                page_size=batch_size,
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

        # 거리 메트릭 가져오기
        distance_metric = self.config.get("distance_metric", "cosine")
        distance_funcs = {"cosine": "<=>", "l2": "<->", "inner_product": "<#>"}
        distance_func = distance_funcs.get(distance_metric, "<=>")

        try:
            # 기본 검색 쿼리
            search_sql = f"""
            SELECT 
                page_content,
                metadata,
                1 - (embedding {distance_func} %s::vector) as similarity
            FROM {collection_name}
            WHERE 1 = 1
            """

            params = [query_embedding]

            # 메타데이터 필터 추가
            if filter:
                for key, value in filter.items():
                    search_sql += " AND metadata->%s = %s"
                    params.extend([key, json.dumps(value)])

            # 임계값 조건 추가
            if threshold is not None:
                search_sql += f" AND 1 - (embedding {distance_func} %s::vector) >= %s"
                params.extend([query_embedding, threshold])

            search_sql += f"""
            ORDER BY embedding {distance_func} %s::vector
            LIMIT %s
            """
            params.extend([query_embedding, k])

            cursor.execute(search_sql, params)
            results = []

            for content, metadata, similarity in cursor.fetchall():
                doc = Document(page_content=content, metadata=metadata or {})
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
                    conditions.append("metadata->%s = %s")
                    params.extend([key, json.dumps(value)])

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
            info = {"name": collection_name, "backend": self.backend_name}

            # 문서 수
            cursor.execute(f"SELECT COUNT(*) FROM {collection_name}")
            info["count"] = cursor.fetchone()[0]

            # 벡터 차원
            if info["count"] > 0:
                cursor.execute(f"SELECT dimension(embedding) FROM {collection_name} LIMIT 1")
                info["dimension"] = cursor.fetchone()[0]
            else:
                info["dimension"] = None

            # 테이블 크기
            cursor.execute("SELECT pg_size_pretty(pg_total_relation_size(%s::regclass))", (collection_name,))
            info["size"] = cursor.fetchone()[0]

            # 인덱스 정보
            cursor.execute(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = %s AND indexdef LIKE '%embedding%'
            """,
                (collection_name,),
            )

            indexes = []
            for idx_name, idx_def in cursor.fetchall():
                index_info = {"name": idx_name}
                if "hnsw" in idx_def:
                    index_info["type"] = "HNSW"
                elif "ivfflat" in idx_def:
                    index_info["type"] = "IVFFlat"
                indexes.append(index_info)

            info["indexes"] = indexes

            return info

        finally:
            cursor.close()
            conn.close()

    @property
    def backend_name(self) -> str:
        """백엔드 이름을 반환합니다."""
        return "pgvector"

    @property
    def required_dependencies(self) -> List[str]:
        """필요한 의존성 패키지 목록을 반환합니다."""
        return ["psycopg2-binary", "pgvector"]
