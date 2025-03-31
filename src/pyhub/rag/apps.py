import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class PyhubRagConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pyhub.rag"

    def ready(self):
        import pyhub.rag.signals  # noqa
