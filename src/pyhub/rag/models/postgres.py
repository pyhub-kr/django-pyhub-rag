import logging
from typing import List, Literal, Type

from asgiref.sync import sync_to_async
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet
from pgvector.django import CosineDistance, HnswIndex, IvfflatIndex, L2Distance

from ..decorators import warn_if_async
from ..fields.postgres import PGVectorField
from .base import AbstractDocument, BaseDocumentQuerySet

logger = logging.getLogger(__name__)


class PGVectorDocumentQuerySet(BaseDocumentQuerySet):
    def _prepare_search_query(self, query_embedding: List[float]) -> QuerySet["AbstractDocument"]:
        """검색 쿼리를 준비하는 내부 메서드"""

        model_cls: Type[AbstractDocument] = self.model
        embedding_field_name = model_cls.get_embedding_field().name

        qs = self.defer(embedding_field_name)

        for index in self.model._meta.indexes:
            if embedding_field_name in index.fields:
                # vector_cosine_ops, halfvec_cosine_ops, etc.
                if any("_cosine_ops" in op for op in index.opclasses):
                    qs = qs.annotate(distance=CosineDistance(embedding_field_name, query_embedding))
                    qs = qs.order_by("distance")
                    return qs
                # vector_l2_ops, halfvec_l2_ops, etc.
                elif any("_l2_ops" in op for op in index.opclasses):
                    qs = qs.annotate(distance=L2Distance(embedding_field_name, query_embedding))
                    qs = qs.order_by("distance")
                    return qs
                else:
                    raise NotImplementedError(f"{index.opclasses}에 대한 검색 구현이 필요합니다.")

        raise ImproperlyConfigured(f"{self.model.__name__} 모델에 embedding 필드에 대한 인덱스를 추가해주세요.")

    @warn_if_async
    def similarity_search(self, query: str, k: int = 4) -> QuerySet["AbstractDocument"]:
        """동기 검색 메서드"""
        model_cls: Type[AbstractDocument] = self.model
        query_embedding = model_cls.embed(query)

        qs = self._prepare_search_query(query_embedding)
        return qs[:k]

    async def similarity_search_async(self, query: str, k: int = 4) -> List["AbstractDocument"]:
        """비동기 검색 메서드"""
        model_cls: Type[AbstractDocument] = self.model
        query_embedding = await model_cls.embed_async(query)

        qs = self._prepare_search_query(query_embedding)
        return await sync_to_async(list)(qs[:k])  # noqa


class PGVectorDocument(AbstractDocument):
    embedding = PGVectorField(editable=False)
    objects = PGVectorDocumentQuerySet.as_manager()

    @classmethod
    def make_hnsw_index(
        cls,
        index_name: str,
        field_type: Literal["vector", "halfvec", "bit"] = "vector",
        operator_class: Literal["cosine", "l2", "l2", "ip", "hamming", "jaccard"] = "cosine",
        m: int = 16,
        ef_construction: int = 64,
    ):
        if field_type == "vector":
            opclass = {
                "cosine": "vector_cosine_ops",
                "l2": "vector_l2_ops",
                "l1": "vector_l1_ops",
                "ip": "vector_ip_ops",
            }[operator_class]
        elif field_type == "halfvec":
            opclass = {
                "cosine": "halfvec_cosine_ops",
                "l2": "halfvec_l2_ops",
                "l1": "halfvec_l1_ops",
                "ip": "halfvec_ip_ops",
            }[operator_class]
        elif field_type == "bit":
            opclass = {
                "hamming": "bit_hamming_ops",
                "jaccard": "bit_jaccard_ops",
            }[operator_class]
        else:
            raise ValueError("Invalid field_type :", field_type)

        return HnswIndex(
            name=index_name,
            fields=["embedding"],
            m=m,
            ef_construction=ef_construction,
            opclasses=[opclass],
        )

    @classmethod
    def ivfflat_index(
        cls,
        index_name: str,
        field_type: Literal["vector", "halfvec", "bit"] = "vector",
        operator_class: Literal["cosine", "l2", "ip", "hamming"] = "cosine",
        lists: int = 100,
    ):
        if field_type == "vector":
            opclass = {
                "cosine": "vector_cosine_ops",
                "l2": "vector_l2_ops",
                "ip": "vector_ip_ops",
            }[operator_class]
        elif field_type == "halfvec":
            opclass = {
                "cosine": "halfvec_cosine_ops",
                "l2": "halfvec_l2_ops",
                "ip": "halfvec_ip_ops",
            }[operator_class]
        elif field_type == "bit":
            opclass = {
                "hamming": "bit_hamming_ops",
            }[operator_class]
        else:
            raise ValueError("Invalid field_type :", field_type)

        return IvfflatIndex(
            name=index_name,
            fields=["embedding"],
            lists=lists,
            opclasses=[opclass],
        )

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)

        def add_error(msg: str, hint: str = None):
            errors.append(checks.Error(msg, hint=hint, obj=cls))

        embedding_field = cls.get_embedding_field()
        embedding_field_name = embedding_field.name

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


__all__ = ["PGVectorDocument"]
