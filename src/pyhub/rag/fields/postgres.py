from pgvector.django import HalfVectorField, VectorField

from pyhub.rag.fields.base import BaseVectorField


class PGVectorField(BaseVectorField):
    def __init__(
        self,
        dimensions=None,
        openai_api_key=None,
        openai_base_url=None,
        embedding_model=None,
        embedding_max_tokens_limit=None,
        **kwargs,
    ):
        super().__init__(
            dimensions=dimensions,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            embedding_model=embedding_model,
            embedding_max_tokens_limit=embedding_max_tokens_limit,
            **kwargs,
        )

        if self.dimensions <= 2000:
            self.vector_field = VectorField(dimensions=self.dimensions, **kwargs)
        else:
            self.vector_field = HalfVectorField(dimensions=self.dimensions, **kwargs)


__all__ = ["PGVectorField"]
