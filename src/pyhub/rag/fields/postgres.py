from typing import Optional

from pgvector.django import HalfVectorField, VectorField

from pyhub.llm.types import LLMEmbeddingModelType
from pyhub.rag.fields.base import BaseVectorField


class PGVectorField(BaseVectorField):
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
        super().__init__(
            dimensions=dimensions,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            google_api_key=google_api_key,
            embedding_model=embedding_model,
            embedding_max_tokens_limit=embedding_max_tokens_limit,
            **kwargs,
        )

        if self.dimensions <= 2000:
            self.vector_field = VectorField(dimensions=self.dimensions, **kwargs)
        else:
            self.vector_field = HalfVectorField(dimensions=self.dimensions, **kwargs)


__all__ = ["PGVectorField"]
