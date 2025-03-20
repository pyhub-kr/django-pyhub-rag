import logging
import sys
import tempfile
from io import StringIO
from pathlib import Path
from typing import Optional

import django
from django.conf import settings
from environ import Env

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
            # https://docs.djangoproject.com/en/dev/topics/cache/
            CACHES={
                # 개당 200KB 기준 * 5,000개 = 1GB
                "default": make_filecache_setting("pyhub_cache", max_entries=5_000, cull_frequency=5),
                "upstage": make_filecache_setting("pyhub_upstage", max_entries=5_000, cull_frequency=5),
                "openai": make_filecache_setting("pyhub_openai", max_entries=5_000, cull_frequency=5),
                "anthropic": make_filecache_setting("pyhub_anthropic", max_entries=5_000, cull_frequency=5),
                "google": make_filecache_setting("pyhub_google", max_entries=5_000, cull_frequency=5),
                "ollama": make_filecache_setting("pyhub_ollama", max_entries=5_000, cull_frequency=5),
            },
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


def make_filecache_setting(
    name: str,
    location_path: Optional[str] = None,
    timeout: Optional[int] = None,
    max_entries: int = 300,
    # 최대치에 도달했을 때 삭제하는 비율 : 3 이면 1/3 삭제, 0 이면 모두 삭제
    cull_frequency: int = 3,
) -> dict:
    if location_path is None:
        location_path = tempfile.gettempdir()

    return {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": f"{location_path}/{name}",
        "TIMEOUT": timeout,
        "OPTIONS": {
            "MAX_ENTRIES": max_entries,
            "CULL_FREQUENCY": cull_frequency,
        },
    }


def load_envs(env_path: Optional[Path] = None):
    if env_path is None:
        env_path = Path.home() / ".pyhub.env"

    env = Env()

    if env_path.exists():
        try:
            env_text = env_path.read_text(encoding="utf-8")
            env.read_env(StringIO(env_text), overwrite=True)
            logger.debug("loaded %s", env_path.name)
        except IOError:
            pass


def init(debug: bool = False, log_level: int = logging.INFO, env_path: Optional[Path] = None):
    init_django(debug=debug, log_level=log_level)
    load_envs(env_path)
