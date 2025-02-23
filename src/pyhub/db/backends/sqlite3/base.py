from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper

from .operations import DatabaseOperations
from .schema import VirtualTableSchemaEditor


class DatabaseWrapper(SQLiteDatabaseWrapper):
    SchemaEditorClass = VirtualTableSchemaEditor
    ops_class = DatabaseOperations
