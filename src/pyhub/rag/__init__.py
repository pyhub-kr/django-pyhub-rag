"""PyHub RAG (Retrieval Augmented Generation) module."""

from .backends.base import (
    BaseVectorStore,
    Document,
    SearchResult,
)
from .detection import (
    detect_vector_backend,
    get_database_config,
    is_backend_available,
)
from .factory import (
    create_postgres_store,
    create_sqlite_store,
    get_vector_store,
    list_available_backends,
)

# 하위 호환성을 위한 레거시 import
from .registry import VectorStoreRegistry

__all__ = [
    # 새로운 단순화된 API
    "get_vector_store",
    "create_sqlite_store", 
    "create_postgres_store",
    "list_available_backends",
    "detect_vector_backend",
    # 유틸리티
    "get_database_config",
    "is_backend_available",
    # 기본 클래스
    "BaseVectorStore",
    "Document", 
    "SearchResult",
    # 하위 호환성 (곧 제거 예정)
    "VectorStoreRegistry",
]
