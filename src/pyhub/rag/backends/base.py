"""Base abstract class for vector store backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Document:
    """벡터 스토어에 저장되는 문서."""

    page_content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """검색 결과."""

    document: Document
    score: float  # 유사도 점수 (0-1, 1이 가장 유사)


class BaseVectorStore(ABC):
    """벡터 스토어 백엔드의 추상 기본 클래스."""

    def __init__(self, config: Dict[str, Any]):
        """
        백엔드를 초기화합니다.

        Args:
            config: 백엔드별 설정 딕셔너리
        """
        self.config = config
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """설정을 검증합니다."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """백엔드가 사용 가능한지 확인합니다 (의존성, 연결 등)."""
        pass

    @abstractmethod
    def create_collection(self, name: str, dimension: int, distance_metric: str = "cosine", **kwargs) -> None:
        """
        벡터 컬렉션(테이블)을 생성합니다.

        Args:
            name: 컬렉션 이름
            dimension: 벡터 차원
            distance_metric: 거리 메트릭 (cosine, l2, inner_product)
            **kwargs: 백엔드별 추가 옵션
        """
        pass

    @abstractmethod
    def drop_collection(self, name: str) -> None:
        """컬렉션을 삭제합니다."""
        pass

    @abstractmethod
    def collection_exists(self, name: str) -> bool:
        """컬렉션이 존재하는지 확인합니다."""
        pass

    @abstractmethod
    def insert(self, collection_name: str, documents: List[Document], batch_size: int = 1000) -> int:
        """
        문서들을 컬렉션에 삽입합니다.

        Args:
            collection_name: 대상 컬렉션
            documents: 삽입할 문서들
            batch_size: 배치 크기

        Returns:
            삽입된 문서 수
        """
        pass

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        threshold: Optional[float] = None,
    ) -> List[SearchResult]:
        """
        유사도 검색을 수행합니다.

        Args:
            collection_name: 검색할 컬렉션
            query_embedding: 쿼리 임베딩
            k: 반환할 결과 수
            filter: 메타데이터 필터
            threshold: 최소 유사도 임계값

        Returns:
            검색 결과 리스트
        """
        pass

    @abstractmethod
    def delete(self, collection_name: str, filter: Dict[str, Any]) -> int:
        """
        필터에 매칭되는 문서들을 삭제합니다.

        Args:
            collection_name: 대상 컬렉션
            filter: 삭제 조건

        Returns:
            삭제된 문서 수
        """
        pass

    @abstractmethod
    def count(self, collection_name: str) -> int:
        """컬렉션의 문서 수를 반환합니다."""
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        컬렉션 정보를 반환합니다.

        Returns:
            컬렉션 정보 (크기, 인덱스, 차원 등)
        """
        pass

    def import_jsonl(
        self, collection_name: str, file_path: Path, batch_size: int = 1000, clear_existing: bool = False
    ) -> int:
        """
        JSONL 파일에서 데이터를 임포트합니다.

        Args:
            collection_name: 대상 컬렉션
            file_path: JSONL 파일 경로
            batch_size: 배치 크기
            clear_existing: 기존 데이터 삭제 여부

        Returns:
            임포트된 문서 수
        """
        import json

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if clear_existing and self.collection_exists(collection_name):
            self.clear_collection(collection_name)

        documents = []
        total_imported = 0

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())

                    # 데이터 검증
                    if "page_content" not in data:
                        raise ValueError(f"Missing 'page_content' at line {line_num}")
                    if "embedding" not in data:
                        raise ValueError(f"Missing 'embedding' at line {line_num}")

                    doc = Document(
                        page_content=data["page_content"],
                        metadata=data.get("metadata", {}),
                        embedding=data["embedding"],
                    )
                    documents.append(doc)

                    # 배치 처리
                    if len(documents) >= batch_size:
                        total_imported += self.insert(collection_name, documents, batch_size)
                        documents = []

                except (json.JSONDecodeError, ValueError) as e:
                    raise ValueError(f"Error at line {line_num}: {e}")

        # 남은 문서 처리
        if documents:
            total_imported += self.insert(collection_name, documents, batch_size)

        return total_imported

    def clear_collection(self, name: str) -> None:
        """컬렉션의 모든 데이터를 삭제합니다."""
        # 기본 구현: 모든 문서 삭제
        self.delete(name, {})

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """백엔드 이름을 반환합니다."""
        pass

    @property
    @abstractmethod
    def required_dependencies(self) -> List[str]:
        """필요한 의존성 패키지 목록을 반환합니다."""
        pass
