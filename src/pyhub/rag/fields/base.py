import logging
from typing import Optional

from django.db import models

from pyhub.rag.settings import rag_settings

logger = logging.getLogger(__name__)


class BaseVectorField(models.Field):
    def __init__(
        self,
        dimensions=None,
        openai_api_key=None,
        openai_base_url=None,
        embedding_model=None,
        embedding_max_tokens_limit=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.vector_field: Optional[models.Field] = None
        self.dimensions = dimensions or rag_settings.RAG_EMBEDDING_DIMENSIONS
        self.openai_api_key = openai_api_key or rag_settings.RAG_OPENAI_API_KEY
        self.openai_base_url = openai_base_url or rag_settings.RAG_OPENAI_BASE_URL
        self.embedding_model = embedding_model or rag_settings.RAG_EMBEDDING_MODEL
        self.embedding_max_tokens_limit = embedding_max_tokens_limit or rag_settings.RAG_EMBEDDING_MAX_TOKENS_LIMIT

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
        if self.vector_field is None:
            raise NotImplementedError("BaseVectorField 클래스를 상속받은 필드를 사용해주세요.")
        return self.vector_field.db_type(connection)

    def get_prep_value(self, value):
        if self.vector_field is None:
            raise NotImplementedError("BaseVectorField 클래스를 상속받은 필드를 사용해주세요.")
        return self.vector_field.get_prep_value(value)

    def from_db_value(self, value, expression, connection):
        if self.vector_field is None:
            raise NotImplementedError("BaseVectorField 클래스를 상속받은 필드를 사용해주세요.")
        return self.vector_field.from_db_value(value, expression, connection)


__all__ = ["BaseVectorField"]
