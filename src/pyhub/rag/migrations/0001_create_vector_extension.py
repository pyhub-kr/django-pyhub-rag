import logging

from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.operations.base import Operation
from django.db.migrations.state import ProjectState

logger = logging.getLogger(__name__)


class VectorExtension(Operation):

    def state_forwards(self, app_label, state):
        """이번 Operation이 모델 상태(state)에 영향을 주지 않으므로 아무런 작업도 수행하지 않습니다."""

    def database_forwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ProjectState,
        to_state: ProjectState,
    ) -> None:
        if schema_editor.connection.vendor == "postgresql":
            from django.contrib.postgres.operations import CreateExtension

            extension = CreateExtension("vector")
            extension.database_forwards(app_label, schema_editor, from_state, to_state)
        else:
            logger.info(f"Vector extension is not supported for the database vendor: {schema_editor.connection.vendor}")

    def database_backwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ProjectState,
        to_state: ProjectState,
    ) -> None:
        if schema_editor.connection.vendor == "postgresql":
            from django.contrib.postgres.operations import CreateExtension

            extension = CreateExtension("vector")
            extension.database_backwards(app_label, schema_editor, from_state, to_state)


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        VectorExtension(),
    ]
