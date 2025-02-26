import logging
from typing import List, Type

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core import checks

from ..fields.sqlite import SQLiteVectorField
from .base import AbstractDocument, BaseDocumentQuerySet

logger = logging.getLogger(__name__)


class SQLiteVectorDocumentQuerySet(BaseDocumentQuerySet):
    async def search(self, query: str, k: int = 4) -> List["AbstractDocument"]:
        model_cls: Type[AbstractDocument] = self.model

        table_name = model_cls._meta.db_table
        field_name = model_cls.get_embedding_field().name

        query_embedding: List[float] = await model_cls.aembed(query)

        field_names = [field.name for field in model_cls._meta.local_fields if field.name != field_name]
        fields_sql = ", ".join(field_names)

        # KNN 쿼리
        raw_query = f"""
            SELECT
              {fields_sql}
            FROM {table_name}
            WHERE {field_name} MATCH vec_f32(?)
            ORDER BY distance
            LIMIT {k};
        """

        qs = self.raw(raw_query=raw_query, params=[str(query_embedding)])

        return await sync_to_async(list)(qs)  # noqa


class SQLiteVectorDocument(AbstractDocument):
    """
    SQLite 환경에서 사용하는 Document 모델
    """

    embedding = SQLiteVectorField(editable=False)
    objects = SQLiteVectorDocumentQuerySet.as_manager()

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)

        def add_error(msg: str, hint: str = None):
            errors.append(checks.Error(msg, hint=hint, obj=cls))

        db_alias = kwargs.get("using") or "default"
        db_settings = settings.DATABASES.get(db_alias, {})
        engine = db_settings.get("ENGINE", "")

        if engine != "pyhub.db.backends.sqlite3":
            add_error(
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
            )

        return errors

    class Meta:
        abstract = True


__all__ = ["SQLiteVectorDocument"]
