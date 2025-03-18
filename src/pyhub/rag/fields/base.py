import logging
from typing import Optional, Union

from django.db import models

from pyhub.llm import GoogleLLM, OpenAILLM
from pyhub.llm.types import (
    GoogleEmbeddingModelType,
    LLMEmbeddingModelType,
    OpenAIEmbeddingModelType,
)
from pyhub.rag.settings import rag_settings
from pyhub.rag.utils import get_literal_values

logger = logging.getLogger(__name__)


class BaseVectorField(models.Field):
    def __init__(
        self,
        dimensions: Optional[int] = None,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        google_api_key: Optional[str] = None,
        embedding_model: Optional[LLMEmbeddingModelType] = None,
        embedding_max_tokens_limit: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.vector_field: Optional[models.Field] = None
        self.dimensions = dimensions or rag_settings.embedding_dimensions
        self.openai_api_key = openai_api_key or rag_settings.openai_api_key
        self.openai_base_url = openai_base_url or rag_settings.openai_base_url
        self.google_api_key = google_api_key or rag_settings.google_api_key
        self.embedding_model = embedding_model or rag_settings.embedding_model
        self.embedding_max_tokens_limit = embedding_max_tokens_limit or rag_settings.embedding_max_tokens_limit

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.update(
            {
                "dimensions": self.dimensions,
                "openai_api_key": self.openai_api_key,
                "openai_base_url": self.openai_base_url,
                "google_api_key": self.google_api_key,
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

    def embed(
        self,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModelType] = None,
    ) -> Union[list[float], list[list[float]]]:

        embedding_model = model or self.embedding_model

        if embedding_model in get_literal_values(OpenAIEmbeddingModelType):
            llm = OpenAILLM(api_key=self.openai_api_key, base_url=self.openai_base_url)
            return llm.embed(input, model=embedding_model)

        elif embedding_model in get_literal_values(GoogleEmbeddingModelType):
            llm = GoogleLLM(api_key=self.google_api_key)
            return llm.embed(input, model=embedding_model)

        raise NotImplementedError(f"Embedding model '{embedding_model}' is not supported yet.")

    async def embed_async(
        self,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModelType] = None,
    ) -> Union[list[float], list[list[float]]]:
        embedding_model = model or self.embedding_model

        if embedding_model in get_literal_values(OpenAIEmbeddingModelType):
            llm = OpenAILLM(api_key=self.openai_api_key, base_url=self.openai_base_url)
            return await llm.embed_async(input, model=embedding_model)

        elif embedding_model in get_literal_values(GoogleEmbeddingModelType):
            llm = GoogleLLM(api_key=self.google_api_key)
            return await llm.embed_async(input, model=embedding_model)

        raise NotImplementedError(f"Embedding model '{embedding_model}' is not supported yet.")


__all__ = ["BaseVectorField"]
