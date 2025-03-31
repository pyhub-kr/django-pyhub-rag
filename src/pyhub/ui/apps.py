import importlib
from pathlib import Path

from django.apps import AppConfig


class PyhubUiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pyhub.ui"

    # django-components의 autodiscover를 켜니, pyhub.ui 앱이 pyhub.web 앱 안에 넣어서 경로 오류 발생.
    # 그래서 pyhub.ui 앱 내에서만 컴포넌트를 찾는 코드 수행
    def ready(self):
        components_dir = Path(__file__).parent.resolve()

        for item in components_dir.iterdir():
            if item.is_dir():
                comp_file = item / f"{item.name}.py"
                if comp_file.is_file():
                    module_path = f"pyhub.ui.{item.name}.{item.name}"
                    importlib.import_module(module_path)
