from django.db import models
from pgvector.django import HalfVectorField
from pgvector.django import VectorField as OrigVectorField

from pyhub.rag.settings import rag_settings


class VectorField(models.Field):
    def __init__(
        self,
        dimensions=None,
        openai_api_key=None,
        openai_base_url=None,
        embedding_model=None,
        embedding_max_tokens_limit=None,
        **kwargs,
    ):
        self.dimensions = dimensions or rag_settings.RAG_EMBEDDING_DIMENSIONS
        self.openai_api_key = openai_api_key or rag_settings.RAG_OPENAI_API_KEY
        self.openai_base_url = openai_base_url or rag_settings.RAG_OPENAI_BASE_URL
        self.embedding_model = embedding_model or rag_settings.RAG_EMBEDDING_MODEL
        self.embedding_max_tokens_limit = embedding_max_tokens_limit or rag_settings.RAG_EMBEDDING_MAX_TOKENS_LIMIT

        self.vector_field_class = OrigVectorField if self.dimensions <= 2000 else HalfVectorField
        self.vector_field = self.vector_field_class(dimensions=self.dimensions, **kwargs)
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.update(
            {
                "dimensions": self.dimensions,
                "openai_api_key": self.openai_api_key,
                "openai_base_url": self.openai_base_url,
                "embedding_model": self.embedding_model,
                "embedding_max_tokens_limit": self.embedding_max_tokens_limit,
            }
        )
        return name, path, args, kwargs

    def db_type(self, connection):
        return self.vector_field.db_type(connection)

    def get_prep_value(self, value):
        return self.vector_field.get_prep_value(value)

    def from_db_value(self, value, expression, connection):
        return self.vector_field.from_db_value(value, expression, connection)


__all__ = ["VectorField"]
