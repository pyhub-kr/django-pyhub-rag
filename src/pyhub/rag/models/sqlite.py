import logging
from typing import List

from asgiref.sync import sync_to_async
from django.core import checks
from django.db import connections
from django.db.models.query import QuerySet

from ..decorators import warn_if_async
from ..fields.sqlite import SQLiteVectorField
from .base import AbstractDocument, BaseDocumentQuerySet

logger = logging.getLogger(__name__)


class SQLiteVectorDocumentQuerySet(BaseDocumentQuerySet):
    def _prepare_search_query(self, query_embedding: List[float]) -> QuerySet["AbstractDocument"]:
        return self.extra(
            select={"distance": "distance"},
            where=["embedding MATCH vec_f32(?)"],
            params=[str(query_embedding)],
            order_by=["distance"],
        ).defer("embedding")

    @warn_if_async
    def similarity_search(self, query: str, k: int = 4) -> QuerySet["AbstractDocument"]:
        query_embedding = self.model.embed(query)
        qs = self._prepare_search_query(query_embedding)
        return qs[:k]

    async def similarity_search_async(self, query: str, k: int = 4) -> List["AbstractDocument"]:
        query_embedding = await self.model.embed_async(query)

        qs = self._prepare_search_query(query_embedding)
        return await sync_to_async(list, thread_sensitive=True)(qs[:k])  # noqa


class SQLiteVectorDocument(AbstractDocument):
    """
    SQLite 환경에서 사용하는 Document 모델
    """

    embedding = SQLiteVectorField(editable=False)
    objects = SQLiteVectorDocumentQuerySet.as_manager()

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)

        using = kwargs.get("using")
        db_alias, env_name, vs_config = cls.get_vs_config(using=using)

        if vs_config and vs_config["ENGINE"] != "pyhub.db.backends.sqlite3":
            errors.append(
                checks.Error(
                    "SQLiteVectorDocument 모델은 pyhub.db.backends.sqlite3 데이터베이스 엔진에서 지원합니다.",
                    hint=(
                        "settings.DATABASES sqlite3 설정에 pyhub.db.backends.sqlite3 데이터베이스 엔진을 적용해주세요.\n"
                        "\n"
                        "\t\tDATABASES = {\n"
                        '\t\t    "default": {\n'
                        '\t\t        "ENGINE": "pyhub.db.backends.sqlite3",  # <-- \n'
                        "\t\t        # ...\n"
                        "\t\t    }\n"
                        "\t\t}\n"
                    ),
                    obj=cls,
                )
            )
        else:
            with connections[db_alias].cursor() as cursor:
                cursor.execute("SELECT EXISTS (SELECT 1 FROM pragma_function_list WHERE name = 'vec_f32');")
                (is_exist,) = cursor.fetchone()
                if not is_exist:  # 1 or 0
                    checks.Error(
                        f"settings.DATABASES['{db_alias}']에 지정된 데이터베이스에 vec0 확장을 찾을 수 없습니다.",
                        hint="sqlite-vec 라이브러리를 설치해주세요.",
                        obj=cls,
                    )

        return errors

    class Meta:
        abstract = True


__all__ = ["SQLiteVectorDocument"]
