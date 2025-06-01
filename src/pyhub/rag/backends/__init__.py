"""Vector store backends for PyHub RAG."""

from typing import TYPE_CHECKING, Dict, Type

if TYPE_CHECKING:
    from .base import BaseVectorStore

# 백엔드 레지스트리
_BACKENDS: Dict[str, str] = {
    "pgvector": "pyhub.rag.backends.pgvector.PgVectorStore",
    "sqlite-vec": "pyhub.rag.backends.sqlite_vec.SqliteVecStore",
}


def get_backend_class(backend_name: str) -> Type["BaseVectorStore"]:
    """백엔드 클래스를 동적으로 로드합니다."""
    if backend_name not in _BACKENDS:
        raise ValueError(f"Unknown backend: {backend_name}. Available: {list(_BACKENDS.keys())}")

    module_path = _BACKENDS[backend_name]
    module_name, class_name = module_path.rsplit(".", 1)

    try:
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to load backend {backend_name}: {e}")


def list_backends() -> list[str]:
    """사용 가능한 백엔드 목록을 반환합니다."""
    return list(_BACKENDS.keys())


__all__ = ["get_backend_class", "list_backends"]
