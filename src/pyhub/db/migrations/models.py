import logging

from django.db.migrations import CreateModel

logger = logging.getLogger(__name__)


class CreateModelOnlySpecificDatabase(CreateModel):
    ONLY_VENDOR = None

    def database_forwards(self, app_label, schema_editor, from_state, to_state) -> None:
        if schema_editor.connection.vendor == self.ONLY_VENDOR:
            logger.info(
                "Creating model %s.%s in %s database",
                app_label,
                self.name,
                self.ONLY_VENDOR,
            )
            super().database_forwards(app_label, schema_editor, from_state, to_state)
        else:
            logger.warning(
                f"{self.__class__.__name__} is not supported for the database vendor: {schema_editor.connection.vendor}"
            )
            logger.info(
                "Skipping model %s.%s creation - not a %s database",
                app_label,
                self.name,
                self.ONLY_VENDOR,
            )

    def database_backwards(self, app_label, schema_editor, from_state, to_state) -> None:
        if schema_editor.connection.vendor == self.ONLY_VENDOR:
            logger.info(
                "Removing model %s.%s from %s database",
                app_label,
                self.name,
                self.ONLY_VENDOR,
            )
            super().database_backwards(app_label, schema_editor, from_state, to_state)
        else:
            logger.info(
                "Skipping model %s.%s removal - not a %s database",
                app_label,
                self.name,
                self.ONLY_VENDOR,
            )


class CreateModelOnlyPostgres(CreateModelOnlySpecificDatabase):
    ONLY_VENDOR = "postgresql"


class CreateModelOnlySqlite(CreateModelOnlySpecificDatabase):
    ONLY_VENDOR = "sqlite"


__all__ = ["CreateModelOnlyPostgres", "CreateModelOnlySqlite"]
