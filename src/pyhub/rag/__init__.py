"""PyHub RAG (Retrieval Augmented Generation) module."""

from .backends.base import (
    BaseVectorStore,
    Document,
    SearchResult,
)
from .registry import (
    VectorStoreRegistry,
    get_vector_store,
    list_available_backends,
)

__all__ = [
    "get_vector_store",
    "list_available_backends",
    "VectorStoreRegistry",
    "BaseVectorStore",
    "Document",
    "SearchResult",
]
