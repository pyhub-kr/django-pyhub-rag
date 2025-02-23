from django.db.backends.sqlite3.operations import (
    DatabaseOperations as OrigDatabaseOperations,
)


class DatabaseOperations(OrigDatabaseOperations):

    def last_executed_query(self, cursor, sql, params):
        """
        Django의 기본 sqlite3 구현에서는 last_executed_query 메서드가 SQL 문자열과 파라미터를 % 연산자로 포맷팅하려 시도합니다.
        하지만 sqlite3는 ? 를 파라미터 플레이스홀더로 사용하기에, % 연산자로 포맷팅 시도 시 TypeError가 발생합니다.

        예를 들어:
        - SQL: "SELECT * FROM table WHERE id = ?"
        - params: [1]

        이런 경우 % 연산자로 포맷팅하면 TypeError가 발생하므로,
        ? 를 %s로 변경하여 Django의 기본 포맷팅 방식을 따르도록 합니다.
        """
        try:
            return super().last_executed_query(cursor, sql, params)
        except TypeError:
            # sqlite3의 ? 파라미터를 Django 스타일의 %s로 변경
            sql = sql.replace("?", "%s")
            return super().last_executed_query(cursor, sql, params)
