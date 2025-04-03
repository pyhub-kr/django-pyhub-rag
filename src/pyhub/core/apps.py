from django.apps import AppConfig

from pyhub import activate_timezone


class PyhubCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pyhub.core"

    def ready(self):
        activate_timezone()