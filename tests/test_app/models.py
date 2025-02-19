from pgvector.django import HnswIndex

from pyhub.rag.models import AbstractDocument


class TestDocument(AbstractDocument):
    class Meta:
        app_label = "test_app"
        indexes = [
            HnswIndex(
                name="test_document_embedding_idx",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            )
        ]
