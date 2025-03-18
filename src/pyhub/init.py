import logging
import sys
from pathlib import Path

import django
from django.conf import settings

logger = logging.getLogger(__name__)


def init_django(debug: bool = False, log_level: int = logging.INFO):
    """
    Django 환경을 초기화하는 함수입니다.
    src 폴더를 루트 경로로 하여 pyhub 디렉토리 내의 모든 앱을 자동으로 등록하고 기본 템플릿을 활성화합니다.
    """

    src_path = Path(__file__).resolve().parent.parent
    if src_path.name == "src":
        sys.path.insert(0, str(src_path))

    if not django.conf.settings.configured:
        pyhub_path = Path(__file__).resolve().parent
        pyhub_apps = []

        # 디렉토리만 검색하고 각 디렉토리가 Django 앱인지 확인
        for item in pyhub_path.iterdir():
            if item.is_dir() and not item.name.startswith("__") and not item.name.startswith("."):
                # apps.py 파일이 있거나 models.py 파일이 있으면 Django 앱으로 간주
                if (item / "apps.py").exists():
                    app_name = f"pyhub.{item.name}"
                    pyhub_apps.append(app_name)

        installed_apps = [
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
            *pyhub_apps,
        ]

        logger.debug("자동으로 감지된 pyhub 앱: %s", ", ".join(pyhub_apps))

        settings.configure(
            DEBUG=debug,
            SECRET_KEY="django-pyhub-rag-insecure-secret-key",
            INSTALLED_APPS=installed_apps,
            TEMPLATES=[
                {
                    "BACKEND": "django.template.backends.django.DjangoTemplates",
                    "DIRS": [],
                    "APP_DIRS": True,
                    "OPTIONS": {
                        "context_processors": [
                            "django.template.context_processors.debug",
                            "django.template.context_processors.request",
                            "django.contrib.auth.context_processors.auth",
                            "django.contrib.messages.context_processors.messages",
                        ],
                    },
                },
            ],
            LOGGING={
                "version": 1,
                "disable_existing_loggers": True,
                "filters": {
                    "require_debug_true": {
                        "()": "django.utils.log.RequireDebugTrue",
                    },
                },
                "formatters": {
                    "color": {
                        "()": "colorlog.ColoredFormatter",
                        "format": "%(log_color)s[%(asctime)s] %(message)s",
                        "log_colors": {
                            "INFO": "green",
                            "WARNING": "yellow",
                            "ERROR": "red",
                            "CRITICAL": "bold_red",
                        },
                    },
                },
                "handlers": {
                    "debug_console": {
                        "level": "DEBUG",
                        "class": "logging.StreamHandler",
                        "filters": ["require_debug_true"],
                        "formatter": "color",
                    },
                },
                "loggers": {
                    "pyhub": {
                        "handlers": ["debug_console"],
                        "level": log_level,
                        "propagate": False,
                    },
                },
            },
        )

        django.setup()

        logging.debug("Django 환경이 초기화되었습니다.")
