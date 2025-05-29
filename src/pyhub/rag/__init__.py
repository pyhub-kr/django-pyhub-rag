"""PyHub RAG (Retrieval Augmented Generation) module."""

from .registry import (
    get_vector_store,
    list_available_backends,
    VectorStoreRegistry,
)
from .backends.base import (
    BaseVectorStore,
    Document,
    SearchResult,
)

__all__ = [
    "get_vector_store",
    "list_available_backends",
    "VectorStoreRegistry",
    "BaseVectorStore",
    "Document",
    "SearchResult",
]