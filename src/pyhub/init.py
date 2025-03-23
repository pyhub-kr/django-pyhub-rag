import logging
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict, Union

import django
import toml
from django.conf import settings
from environ import Env

logger = logging.getLogger(__name__)


src_path = Path(__file__).resolve().parent.parent
if src_path.name == "src":
    sys.path.insert(0, str(src_path))


class PromptTemplates(TypedDict):
    system: str
    user: str


@dataclass
class PyhubTomlSetting:
    env: dict[str, str]
    prompt_templates: dict[str, PromptTemplates]


class TemplateSetting(TypedDict):
    BACKEND: Literal["django.template.backends.django.DjangoTemplates"]
    DIRS: list[Union[str, Path]]
    APP_DIRS: bool
    OPTIONS: dict[str, list]


@dataclass
class PyhubSetting:
    DEBUG: bool
    SECRET_KEY: str
    ALLOWED_HOSTS: list[str]
    CSRF_TRUSTED_ORIGINS: list[str]
    INSTALLED_APPS: list[str]
    TEMPLATES: list[TemplateSetting]
    DATABASE_ROUTERS: list[str]
    DATABASES: dict[str, dict]
    AUTH_PASSWORD_VALIDATORS: list[dict[str, str]]
    CACHES: dict[str, dict]
    LOGGING: dict[str, Any]
    LANGUAGE_CODE: str
    TIME_ZONE: str
    USE_I18N: bool
    USE_TZ: bool
    STATIC_URL: str
    STATIC_ROOT: Path
    STATICFILES_DIRS: list[Union[str, Path]]
    MEDIA_URL: str
    MEDIA_ROOT: Path
    DEFAULT_AUTO_FIELD: Literal["django.db.models.BigAutoField"]
    SERVICE_DOMAIN: Optional[str]
    NCP_MAP_CLIENT_ID: Optional[str]
    NCP_MAP_CLIENT_SECRET: Optional[str]
    PROMPT_TEMPLATES: dict[str, PromptTemplates]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_settings(
    base_dir: Optional[Path] = None,
    debug: Optional[bool] = None,
    debug_default_value: bool = False,
    log_level: Optional[int] = None,
    toml_path: Optional[Path] = None,
    env_path: Optional[Path] = None,
) -> PyhubSetting:

    toml_settings = load_toml(toml_path=toml_path, load_env=True)
    prompt_templates = toml_settings.prompt_templates if toml_settings else {}

    load_envs(env_path=env_path)

    env = Env()

    if base_dir is None:
        base_dir = Path(os.curdir).absolute()

    if debug is None:
        debug = env.bool("DEBUG", default=debug_default_value)

    if log_level is None:
        log_level = logging.DEBUG if debug else logging.INFO

    pyhub_path = Path(__file__).resolve().parent
    pyhub_apps = []

    # 디렉토리만 검색하고 각 디렉토리가 Django 앱인지 확인
    for item in pyhub_path.iterdir():
        if item.is_dir() and not item.name.startswith("__") and not item.name.startswith("."):
            # apps.py 파일이 있거나 models.py 파일이 있으면 Django 앱으로 간주
            if (item / "apps.py").exists():
                app_name = f"pyhub.{item.name}"
                pyhub_apps.append(app_name)

    logger.debug("자동으로 감지된 pyhub 앱: %s", ", ".join(pyhub_apps))

    installed_apps = [
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        *pyhub_apps,
    ]

    return PyhubSetting(
        DEBUG=debug,
        SECRET_KEY=os.environ.get(
            "SECRET_KEY",
            default="django-insecure-2%6ln@_fnpi!=ivjk(=)e7nx!7abp9d2e3f-+!*o=4s(bd1ynf",
        ),
        ALLOWED_HOSTS=env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", ".ngrok-free.app"]),
        CSRF_TRUSTED_ORIGINS=env.list("CSRF_TRUSTED_ORIGINS", default=[]),
        INSTALLED_APPS=installed_apps,
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [
                    *([base_dir / "templates"] if base_dir is not None else []),
                ],
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
        # Database
        # https://docs.djangoproject.com/en/5.1/ref/settings/#databases
        DATABASE_ROUTERS=["pyhub.routers.Router"],
        DATABASES=get_databases(base_dir),
        # Password validation
        # https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators
        AUTH_PASSWORD_VALIDATORS=[
            {
                "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
            },
            {
                "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
            },
            {
                "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
            },
            {
                "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
            },
        ],
        #
        # Logging
        #
        LOGGING={
            "version": 1,
            "disable_existing_loggers": True,
            "filters": {
                # "require_debug_true": {
                #     "()": "django.utils.log.RequireDebugTrue",
                # },
            },
            "formatters": {
                "color": {
                    "()": "colorlog.ColoredFormatter",
                    "format": "%(log_color)s[%(asctime)s] %(message)s",
                    "log_colors": {
                        "DEBUG": "blue",
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
                    # "filters": ["require_debug_true"],
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
        # Internationalization
        # https://docs.djangoproject.com/en/5.1/topics/i18n/
        LANGUAGE_CODE=env.str("LANGUAGE_CODE", default="ko-kr"),
        TIME_ZONE=env.str("TIME_ZONE", default="UTC"),
        USE_I18N=True,
        USE_TZ=True,
        # Static files (CSS, JavaScript, Images)
        # https://docs.djangoproject.com/en/5.1/howto/static-files/
        STATIC_URL=env.str("STATIC_URL", default="static/"),
        STATIC_ROOT=env.path("STATIC_ROOT", default=base_dir / "staticfiles"),
        STATICFILES_DIRS=[],
        MEDIA_URL=env.str("MEDIA_URL", default="media/"),
        MEDIA_ROOT=env.path("MEDIA_ROOT", default=base_dir / "mediafiles"),
        # Default primary key field type
        # https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        # api
        SERVICE_DOMAIN=env.str("SERVICE_DOMAIN", default=None),
        NCP_MAP_CLIENT_ID=env.str("NCP_MAP_CLIENT_ID", default=None),
        NCP_MAP_CLIENT_SECRET=env.str("NCP_MAP_CLIENT_SECRET", default=None),
        PROMPT_TEMPLATES=prompt_templates,
    )


def get_databases(base_dir: Path):
    env = Env()

    DEFAULT_DATABASE = f"sqlite:///{ base_dir / 'db.sqlite3'}"
    _databases = {
        "default": env.db("DATABASE_URL", default=DEFAULT_DATABASE),
    }

    for db_name in _databases:
        if _databases[db_name]["ENGINE"] == "django.db.backends.sqlite3":
            _databases[db_name]["ENGINE"] = "pyhub.db.backends.sqlite3"

            _databases[db_name].setdefault("OPTIONS", {})

            PRAGMA_FOREIGN_KEYS = env.str("PRAGMA_FOREIGN_KEYS", default="ON")
            PRAGMA_JOURNAL_MODE = env.str("PRAGMA_JOURNAL_MODE", default="WAL")
            PRAGMA_SYNCHRONOUS = env.str("PRAGMA_SYNCHRONOUS", default="NORMAL")
            PRAGMA_BUSY_TIMEOUT = env.int("PRAGMA_BUSY_TIMEOUT", default=5000)
            PRAGMA_TEMP_STORE = env.str("PRAGMA_TEMP_STORE", default="MEMORY")
            PRAGMA_MMAP_SIZE = env.int("PRAGMA_MMAP_SIZE", default=134_217_728)
            PRAGMA_JOURNAL_SIZE_LIMIT = env.int("PRAGMA_JOURNAL_SIZE_LIMIT", default=67_108_864)
            PRAGMA_CACHE_SIZE = env.int("PRAGMA_CACHE_SIZE", default=2000)
            # "IMMEDIATE" or "EXCLUSIVE"
            PRAGMA_TRANSACTION_MODE = env.str("PRAGMA_TRANSACTION_MODE", default="IMMEDIATE")

            init_command = (
                f"PRAGMA foreign_keys={PRAGMA_FOREIGN_KEYS};"
                f"PRAGMA journal_mode = {PRAGMA_JOURNAL_MODE};"
                f"PRAGMA synchronous = {PRAGMA_SYNCHRONOUS};"
                f"PRAGMA busy_timeout = {PRAGMA_BUSY_TIMEOUT};"
                f"PRAGMA temp_store = {PRAGMA_TEMP_STORE};"
                f"PRAGMA mmap_size = {PRAGMA_MMAP_SIZE};"
                f"PRAGMA journal_size_limit = {PRAGMA_JOURNAL_SIZE_LIMIT};"
                f"PRAGMA cache_size = {PRAGMA_CACHE_SIZE};"
            )

            # https://gcollazo.com/optimal-sqlite-settings-for-django/
            _databases[db_name]["OPTIONS"].update(
                {
                    "init_command": init_command,
                    "transaction_mode": PRAGMA_TRANSACTION_MODE,
                }
            )

    return _databases


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


def load_envs(env_path: Optional[Union[str, Path]] = None, overwrite: bool = True) -> None:
    if env_path is None:
        env_path = Path.home() / ".pyhub.env"
    elif isinstance(env_path, str):
        env_path = Path(env_path)

    env = Env()

    if env_path.exists():
        try:
            env_text = env_path.read_text(encoding="utf-8")
            env.read_env(StringIO(env_text), overwrite=overwrite)
            logger.debug("loaded %s", env_path.name)
        except IOError:
            pass


def load_toml(
    toml_path: Optional[Union[str, Path]] = None,
    load_env: bool = False,
) -> Optional[PyhubTomlSetting]:
    if toml_path is None:
        toml_path = Path.home() / ".pyhub.toml"
    elif isinstance(toml_path, str):
        toml_path = Path(toml_path)

    if toml_path.is_file() is False:
        return None

    obj: dict

    try:
        with toml_path.open("r", encoding="utf-8") as f:
            obj = toml.load(f)
    except IOError:
        logger.warning("failed to load %s", toml_path)
        return None

    # 환경변수 설정
    env_dict: dict = obj.get("env", {})

    if env_dict:
        env = {}
        for k, v in env_dict.items():
            env[k] = v
            if load_env:
                os.environ[k] = v
    else:
        env = {}

    if "prompt_templates" in obj:
        prompt_templates = {}
        for type, prompt in obj["prompt_templates"].items():
            prompt_templates[type] = PromptTemplates(
                system=prompt["system"],
                user=prompt["user"],
            )
    else:
        prompt_templates = {}

    return PyhubTomlSetting(env=env, prompt_templates=prompt_templates)


def init(
    debug: bool = False,
    log_level: Optional[int] = None,
    toml_path: Optional[Path] = None,
    env_path: Optional[Path] = None,
):
    if not django.conf.settings.configured:
        pyhub_settings = make_settings(
            debug=debug,
            log_level=log_level,
            toml_path=toml_path,
            env_path=env_path,
        )
        settings.configure(**pyhub_settings.to_dict())
        django.setup()
        logging.debug("Django 환경이 초기화되었습니다.")
