import asyncio
import logging
from typing import List, Union, cast

import openai
import tiktoken
from asgiref.sync import async_to_sync, sync_to_async
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Index
from django_lifecycle import BEFORE_CREATE, BEFORE_UPDATE, LifecycleModelMixin, hook
from pgvector.django import CosineDistance, HnswIndex, IvfflatIndex, L2Distance

from pyhub.rag.fields import VectorField
from pyhub.rag.settings import rag_settings
from pyhub.rag.utils import make_groups_by_length
from pyhub.rag.validators import MaxTokenValidator

logger = logging.getLogger(__name__)


class DocumentQuerySet(models.QuerySet):

    def bulk_create(self, objs, *args, max_retry=3, interval=60, **kwargs):
        async_to_sync(self._assign_embeddings)(objs, max_retry, interval)
        return super().bulk_create(objs, *args, **kwargs)

    async def abulk_create(self, objs, *args, max_retry=3, interval=60, **kwargs):
        await self._assign_embeddings(objs, max_retry, interval)
        return await super().abulk_create(objs, *args, **kwargs)

    async def search(self, query: str, k: int = 4) -> List["Document"]:
        query_embedding: List[float] = await self.model.aembed(query)

        qs = None
        index: Index
        for index in self.model._meta.indexes:
            if "embedding" in index.fields:
                # vector_cosine_ops, halfvec_cosine_ops, etc.
                if any("_cosine_ops" in cls for cls in index.opclasses):
                    qs = (qs or self).annotate(distance=CosineDistance("embedding", query_embedding))
                    qs = qs.order_by("distance")
                # vector_l2_ops, halfvec_l2_ops, etc.
                elif any("_l2_ops" in cls for cls in index.opclasses):
                    qs = (qs or self).annotate(distance=L2Distance("embedding", query_embedding))
                    qs = qs.order_by("distance")
                else:
                    raise NotImplementedError(f"{index.opclasses}에 대한 검색 구현이 필요합니다.")

        if qs is None:
            raise ImproperlyConfigured(f"{self.model.__name__} 모델에 embedding 필드에 대한 인덱스를 추가해주세요.")

        return await sync_to_async(list)(qs[:k])

    async def _assign_embeddings(self, objs, max_retry=3, interval=60):
        non_embedding_objs = [obj for obj in objs if not obj.embedding]

        if len(non_embedding_objs) > 0:

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
                    except openai.RateLimitError as e:
                        if retry == max_retry:
                            raise e
                        else:
                            msg = "Rate limit exceeded. Retry after %s seconds... : %s"
                            logger.warning(msg, interval, e)
                            await asyncio.sleep(interval)

            for obj, embedding in zip(non_embedding_objs, embeddings):
                obj.embedding = embedding

    def __repr__(self):
        return repr(list(self))


class Document(LifecycleModelMixin, models.Model):
    page_content = models.TextField()
    metadata = models.JSONField(default=dict)
    embedding = VectorField(
        dimensions=rag_settings.RAG_EMBEDDING_DIMENSIONS,
        editable=False,
    )

    objects = DocumentQuerySet.as_manager()

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
        return cast(VectorField, cls._meta.get_field("embedding"))

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
    def embed(cls, input: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        client = openai.Client(
            api_key=cls.get_embedding_field().openai_api_key,
            base_url=cls.get_embedding_field().openai_base_url,
        )
        response = client.embeddings.create(
            input=input,
            model=cls.get_embedding_field().embedding_model,
        )
        if isinstance(input, str):
            return response.data[0].embedding
        return [v.embedding for v in response.data]

    @classmethod
    async def aembed(cls, input: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        client = openai.AsyncClient(
            api_key=cls.get_embedding_field().openai_api_key,
            base_url=cls.get_embedding_field().openai_base_url,
        )
        response = await client.embeddings.create(
            input=input,
            model=cls.get_embedding_field().embedding_model,
        )
        if isinstance(input, str):
            return response.data[0].embedding
        return [v.embedding for v in response.data]

    @classmethod
    def get_token_size(cls, text: str) -> int:
        encoding: tiktoken.Encoding = tiktoken.encoding_for_model(cls.get_embedding_field().embedding_model)
        token: List[int] = encoding.encode(text or "")
        return len(token)

    @classmethod
    def check(cls, **kwargs):
        embedding_field_name = "embedding"

        errors = super().check(**kwargs)

        def add_error(msg: str, hint: str = None):
            errors.append(checks.Error(msg, hint=hint, obj=cls))

        embedding_field = cls.get_embedding_field()

        for index in cls._meta.indexes:
            if embedding_field_name in index.fields:
                if isinstance(index, (HnswIndex, IvfflatIndex)):
                    if embedding_field.dimensions <= 2000:
                        for opclass_name in index.opclasses:
                            if "halfvec_" in opclass_name:
                                add_error(
                                    f"{embedding_field.name} 필드는 {embedding_field.__class__.__name__} 타입으로서 "
                                    f"{opclass_name}를 지원하지 않습니다.",
                                    hint=f"{opclass_name.replace('halfvec_', 'vector_')}로 변경해주세요.",
                                )
                    else:
                        for opclass_name in index.opclasses:
                            if "vector_" in opclass_name:
                                add_error(
                                    f"{embedding_field.name} 필드는 {embedding_field.__class__.__name__} 타입으로서 "
                                    f"{opclass_name}를 지원하지 않습니다.",
                                    hint=f"{opclass_name.replace('vector_', 'halfvec_')}로 변경해주세요.",
                                )
                else:
                    add_error(
                        f"Document 모델 check 메서드에서 {index.__class__.__name__}에 대한 확인이 누락되었습니다.",
                        hint=f"{index.__class__.__name__} 인덱스에 대한 check 루틴을 보완해주세요.",
                    )

        return errors

    class Meta:
        abstract = True


__all__ = ["Document"]
