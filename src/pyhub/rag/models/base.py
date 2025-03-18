import asyncio
import logging
from typing import Union, cast

import tiktoken
from asgiref.sync import async_to_sync
from django.db import models
from django_lifecycle import BEFORE_CREATE, BEFORE_UPDATE, LifecycleModelMixin, hook
from typing_extensions import Optional

from pyhub.llm.types import LLMEmbeddingModelType

from ...llm.exceptions import RateLimitError
from .. import django_lifecycle  # noqa
from ..fields import BaseVectorField
from ..utils import make_groups_by_length
from ..validators import MaxTokenValidator
from . import patch  # noqa

logger = logging.getLogger(__name__)


class BaseDocumentQuerySet(models.QuerySet):
    def as_retriever(self, k: int = 4):
        queryset = self

        class QuerySetRetriever:
            def __call__(self, input: str) -> list["AbstractDocument"]:
                return self.invoke(input)

            def invoke(self, input: str) -> list["AbstractDocument"]:
                return list(queryset.similarity_search(input, k=k))

            async def ainvoke(self, input: str) -> list["AbstractDocument"]:
                return await queryset.similarity_search_async(input, k=k)

        return QuerySetRetriever()

    def bulk_create(self, objs, *args, max_retry=3, interval=60, **kwargs):
        async_to_sync(self._assign_embeddings)(objs, max_retry, interval)
        return super().bulk_create(objs, *args, **kwargs)

    async def abulk_create(self, objs, *args, max_retry=3, interval=60, **kwargs):
        await self._assign_embeddings(objs, max_retry, interval)
        return await super().abulk_create(objs, *args, **kwargs)

    async def _assign_embeddings(self, objs, max_retry=3, interval=60):
        non_embedding_objs = [obj for obj in objs if not obj.embedding]

        if non_embedding_objs:
            embeddings = []

            groups = make_groups_by_length(
                text_list=[obj.page_content for obj in non_embedding_objs],
                group_max_length=self.model.get_embedding_field().embedding_max_tokens_limit,
                length_func=self.model.get_token_size,
            )

            for group in groups:
                for retry in range(1, max_retry + 1):
                    try:
                        embeddings.extend(self.model.embed(group))
                        break
                    except RateLimitError as e:
                        if retry == max_retry:
                            raise e
                        else:
                            msg = "Rate limit exceeded. Retry after %s seconds... : %s"
                            logger.warning(msg, interval, e)
                            await asyncio.sleep(interval)

            for obj, embedding in zip(non_embedding_objs, embeddings):
                obj.embedding = embedding

    def similarity_search(self, query: str, k: int = 4) -> list["AbstractDocument"]:
        raise NotImplementedError

    async def similarity_search_async(self, query: str, k: int = 4) -> list["AbstractDocument"]:
        raise NotImplementedError

    def __repr__(self):
        return repr(list(self))


class AbstractDocument(LifecycleModelMixin, models.Model):
    page_content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    embedding = BaseVectorField(editable=False)

    objects = BaseDocumentQuerySet.as_manager()

    def __repr__(self):
        return f"Document(metadata={self.metadata}, page_content={self.page_content!r})"

    def __str__(self):
        return self.__repr__()

    def update_embedding(self, is_force: bool = False) -> None:
        """강제 업데이트 혹은 임베딩 데이터가 없는 경우에만 임베딩 데이터를 생성합니다."""
        if is_force or not self.embedding:
            self.embedding = self.embed(self.page_content)

    @classmethod
    def get_embedding_field(cls):
        return cast(BaseVectorField, cls._meta.get_field("embedding"))

    def clean(self):
        super().clean()
        validator = MaxTokenValidator(self.get_embedding_field().embedding_model)
        validator(self.page_content)

    @hook(BEFORE_CREATE)
    def on_before_create(self):
        # 생성 시에 임베딩 데이터가 저장되어있지 않으면 임베딩 데이터를 생성합니다.
        self.update_embedding()

    @hook(BEFORE_UPDATE, when="page_content", has_changed=True)
    def on_before_update(self):
        # page_content 변경 시 임베딩 데이터를 생성합니다.
        self.update_embedding(is_force=True)

    @classmethod
    def embed(
        cls,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModelType] = None,
    ) -> Union[list[float], list[list[float]]]:
        field = cls.get_embedding_field()
        return field.embed(input, model)

    @classmethod
    async def embed_async(
        cls,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModelType] = None,
    ) -> Union[list[float], list[list[float]]]:
        field = cls.get_embedding_field()
        return await field.embed_async(input, model)

    @classmethod
    def get_token_size(cls, text: str) -> int:
        encoding: tiktoken.Encoding = tiktoken.encoding_for_model(cls.get_embedding_field().embedding_model)
        token: list[int] = encoding.encode(text or "")
        return len(token)

    class Meta:
        abstract = True


__all__ = ["AbstractDocument", "BaseDocumentQuerySet"]
