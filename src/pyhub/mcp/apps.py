import logging
from importlib import import_module

from django.apps import AppConfig, apps


logger = logging.getLogger(__name__)


class McpConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pyhub.mcp"

    def ready(self):
        for app_config in apps.get_app_configs():
            app_name = app_config.module.__name__

            try:
                import_module(f"{app_name}.mcp_tools")
            except ImportError:
                pass
            else:
                logger.debug("Imported %s.mcp_tools", app_name)
