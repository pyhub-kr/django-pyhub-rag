import logging
import re
from typing import List, Tuple

from django.db.backends.sqlite3.schema import DatabaseSchemaEditor as SQLiteSchemaEditor

logger = logging.getLogger(__name__)


class VirtualTableSchemaEditor(SQLiteSchemaEditor):

    def table_sql(self, model) -> Tuple[str, List]:
        from pyhub.rag.fields.sqlite import SQLiteVectorField

        sql, params = super().table_sql(model)

        # makemigrations나 sqlmigrate 시점에서 사용되는 모델은 각 앱의 장고 모델이 아니라
        # __fake__ 모듈에 생성된 "가짜(frozen)" 모델이기에 모델 클래스의 부모 클래스 검증으로는 Document 모델인지 확인이 불가
        # 그래서 embedding 필드에 SQLiteVectorField가 있는 지 검사하기

        is_create_vec0_table = any(isinstance(field, SQLiteVectorField) for field in model._meta.local_fields)

        if is_create_vec0_table:
            pattern = r'^CREATE TABLE\s+(["\'])(.*?)\1\s*\('
            replacement = r"CREATE VIRTUAL TABLE \1\2\1 using vec0("

            sql = re.sub(pattern, replacement, sql)

            # 생성 컬럼명에 쌍따옴표(")가 포함되어 있으면 제거
            # 컬럼명에서 쌍따옴표 제거 (예: "id" -> id)
            sql = sql.replace('"', "")

            # id 컬럼이 NOT NULL이 있으면 아래 오류 발생 => NOT NULL 제약조건 제거
            # OperationalError: Expected integer for INTEGER metadata column id, received NULL
            sql = re.sub(r"(id\s+[a-zA-Z\d]+)\s+NOT\s+NULL", r"\1", sql)

            # float[] 필드에는 NOT NULL 제약조건이 없으므로 제거하고
            # 이후 조회 시에 MATCH 절에서 자동으로 cosine distance를 활용하기
            # TODO: 다양한 distance 지원하기
            sql = re.sub(r"(float\[\d*\]) NOT NULL", r"\1 distance_metric=cosine", sql)

            logger.debug("translated to sqlite3 vec0 virtual table")

        return sql, params
