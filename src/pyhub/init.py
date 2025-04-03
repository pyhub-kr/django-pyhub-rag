import logging
import os
import sys
import tempfile
import zoneinfo
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Literal, Optional, TypedDict, Union

import django
import toml
from django.conf import settings
from django.utils import timezone
from django_components import ComponentsSettings
from environ import Env
from mcp.server.fastmcp.server import Settings as FastmcpSettings

from pyhub.versions import notify_if_update_available

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
    BASE_DIR: Path
    SECRET_KEY: str
    INTERNAL_IPS: list[str]
    ALLOWED_HOSTS: list[str]
    CSRF_TRUSTED_ORIGINS: list[str]
    INSTALLED_APPS: list[str]
    MIDDLEWARE: list[str]
    TEMPLATES: list[TemplateSetting]
    DATABASE_ROUTERS: list[str]
    DATABASES: dict[str, dict]
    AUTH_USER_MODEL: str
    AUTH_PASSWORD_VALIDATORS: list[dict[str, str]]
    CACHES: dict[str, dict]
    LOGGING: dict[str, Any]
    LANGUAGE_CODE: str
    TIME_ZONE: str
    USER_DEFAULT_TIME_ZONE: str
    USE_I18N: bool
    USE_TZ: bool
    STATIC_URL: str
    STATIC_ROOT: Path
    STATICFILES_DIRS: list[Union[str, Path]]
    STATICFILES_FINDERS: list[str]
    MEDIA_URL: str
    MEDIA_ROOT: Path
    DEFAULT_AUTO_FIELD: Literal["django.db.models.BigAutoField"]
    SERVICE_DOMAIN: Optional[str]
    NCP_MAP_CLIENT_ID: Optional[str]
    NCP_MAP_CLIENT_SECRET: Optional[str]
    PROMPT_TEMPLATES: dict[str, PromptTemplates]
    CRISPY_ALLOWED_TEMPLATE_PACKS: Literal["tailwind"]
    CRISPY_TEMPLATE_PACK: Literal["tailwind"]
    COMPONENTS: ComponentsSettings
    TEST_RUNNER: str
    FASTMCP_SETTINGS: Optional[FastmcpSettings]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_settings(
    base_dir: Optional[Path] = None,
    debug: Optional[bool] = None,
    debug_default_value: bool = False,
    log_level: Optional[int] = None,
    toml_path: Optional[Path] = None,
    env_path: Optional[Path] = None,
    additional_apps: Optional[list[str]] = None,
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

    #
    # ~/.pyhub/ 경로 아래에 db/static/media 디폴트 경로 설정
    #

    pyhub_config_path = Path.home() / ".pyhub"
    pyhub_config_path.mkdir(parents=True, exist_ok=True)

    # DATABASE_URL 환경변수가 없다면, 디폴트로 ~/.pyhub/ 경로에 db.sqlite3 지정
    if "DATABASE_URL" not in os.environ:
        default_sqlite3_path = pyhub_config_path / "db.sqlite3"
        DEFAULT_DATABASE = f"sqlite:///{default_sqlite3_path}"
        os.environ["DATABASE_URL"] = DEFAULT_DATABASE

    if "STATIC_ROOT" not in os.environ:
        default_static_root_path = pyhub_config_path / "staticfiles"
        default_static_root_path.mkdir(parents=True, exist_ok=True)
        os.environ["STATIC_ROOT"] = str(default_static_root_path)

    if "MEDIA_ROOT" not in os.environ:
        default_media_root_path = pyhub_config_path / "mediafiles"
        default_media_root_path.mkdir(parents=True, exist_ok=True)
        os.environ["MEDIA_ROOT"] = str(default_media_root_path)

    #
    # settings 설정 생성
    #

    return PyhubSetting(
        DEBUG=debug,
        BASE_DIR=base_dir,
        SECRET_KEY=os.environ.get(
            "SECRET_KEY",
            default="django-insecure-2%6ln@_fnpi!=ivjk(=)e7nx!7abp9d2e3f-+!*o=4s(bd1ynf",
        ),
        INTERNAL_IPS=env.list("INTERNAL_IPS", default=["127.0.0.1"]),
        ALLOWED_HOSTS=env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", ".ngrok-free.app"]),
        CSRF_TRUSTED_ORIGINS=env.list("CSRF_TRUSTED_ORIGINS", default=[]),
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
            "django_components",
            "django_cotton.apps.SimpleAppConfig",
            "django_rich",
            "django_typer",
            "cotton_heroicons",
            "django_extensions",
            "django_htmx",
            *(["debug_toolbar"] if debug else []),
            "crispy_forms",
            "crispy_tailwind",
            "template_partials.apps.SimpleAppConfig",  # 2개의 AppConfig가 제공
            *pyhub_apps,
            *(additional_apps or []),
        ],
        MIDDLEWARE=[
            *(["debug_toolbar.middleware.DebugToolbarMiddleware"] if debug else []),
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "pyhub.ui.middleware.TimezoneMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            "django_components.middleware.ComponentDependencyMiddleware",
            "django_htmx.middleware.HtmxMiddleware",
        ],
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [
                    *([base_dir / "templates"] if base_dir is not None else []),
                    pyhub_path / "templates",
                ],
                "APP_DIRS": False,
                "OPTIONS": {
                    "builtins": [
                        "django_components.templatetags.component_tags",
                        "pyhub.ui.templatetags.components_tags",
                        "pyhub.ui.templatetags.cotton_tags",
                        "template_partials.templatetags.partials",
                    ],
                    "context_processors": [
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ],
                    "loaders": [
                        (
                            "template_partials.loader.Loader",
                            [
                                (
                                    "django.template.loaders.cached.Loader",
                                    [
                                        "django_cotton.cotton_loader.Loader",
                                        "django_components.template_loader.Loader",
                                        "django.template.loaders.filesystem.Loader",
                                        "django.template.loaders.app_directories.Loader",
                                    ],
                                )
                            ],
                        ),
                    ],
                },
            },
        ],
        # https://docs.djangoproject.com/en/dev/topics/cache/
        CACHES={
            # 개당 200KB 기준 * 5,000개 = 1GB
            "default": make_filecache_setting("pyhub_cache", max_entries=5_000, cull_frequency=5, timeout=86400 * 30),
            "upstage": make_filecache_setting("pyhub_upstage", max_entries=5_000, cull_frequency=5, timeout=86400 * 30),
            "openai": make_filecache_setting("pyhub_openai", max_entries=5_000, cull_frequency=5, timeout=86400 * 30),
            "anthropic": make_filecache_setting(
                "pyhub_anthropic", max_entries=5_000, cull_frequency=5, timeout=86400 * 30
            ),
            "google": make_filecache_setting("pyhub_google", max_entries=5_000, cull_frequency=5, timeout=86400 * 30),
            "ollama": make_filecache_setting("pyhub_ollama", max_entries=5_000, cull_frequency=5, timeout=86400 * 30),
            "locmem": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "pyhub_locmem",
            },
            "dummy": {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            },
        },
        # Database
        # https://docs.djangoproject.com/en/5.1/ref/settings/#databases
        DATABASE_ROUTERS=["pyhub.routers.Router"],
        DATABASES=get_databases(base_dir),
        AUTH_USER_MODEL=env.str("AUTH_USER_MODEL", default="auth.User"),
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
                "require_debug_true": {
                    "()": "django.utils.log.RequireDebugTrue",
                },
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
                "console": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "formatter": "color",
                },
                "debug_console": {
                    "level": "DEBUG",
                    "class": "logging.StreamHandler",
                    "filters": ["require_debug_true"],
                    "formatter": "color",
                },
            },
            "loggers": {
                "django.request": {
                    "handlers": ["console"],
                    "level": log_level,
                    "propagate": False,
                },
                "pyhub": {
                    "handlers": ["console"],
                    "level": log_level,
                    "propagate": False,
                },
                **{
                    _app: {
                        "handlers": ["console"],
                        "level": "INFO",
                        "propagate": False,
                    }
                    for _app in [
                        "pyhub.rag",
                        "pyhub.routers",
                        "django_components",
                        "django_lifecycle",
                    ]
                },
                # "django_components": {
                #     "level": 5,
                #     "handlers": ["debug_console"],
                # },
                "mcp.server": {
                    "handlers": ["console"],
                    "level": log_level,
                    "propagate": False,
                },
            },
        },
        # Internationalization
        # https://docs.djangoproject.com/en/5.1/topics/i18n/
        LANGUAGE_CODE=env.str("LANGUAGE_CODE", default="ko-kr"),
        TIME_ZONE=env.str("TIME_ZONE", default="UTC"),
        USER_DEFAULT_TIME_ZONE=env.str("USER_DEFAULT_TIME_ZONE", default="UTC"),
        USE_I18N=True,
        USE_TZ=True,
        # Static files (CSS, JavaScript, Images)
        # https://docs.djangoproject.com/en/5.1/howto/static-files/
        STATIC_URL=env.str("STATIC_URL", default="static/"),
        STATIC_ROOT=env.path("STATIC_ROOT", default=base_dir / "staticfiles"),
        STATICFILES_DIRS=[
            # core 앱의 static 경로를 사용하기에, 별도 static 경로를 사용하지 않겠습니다.
            # pyhub_path / "static",
        ],
        STATICFILES_FINDERS=[
            # Default finders
            "django.contrib.staticfiles.finders.FileSystemFinder",
            "django.contrib.staticfiles.finders.AppDirectoriesFinder",
            # Django components
            "django_components.finders.ComponentsFileSystemFinder",
        ],
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
        # https://github.com/django-crispy-forms/crispy-tailwind
        CRISPY_ALLOWED_TEMPLATE_PACKS="tailwind",
        CRISPY_TEMPLATE_PACK="tailwind",
        # https://django-components.github.io/django-components/latest/overview/installation/
        COMPONENTS=ComponentsSettings(
            autodiscover=False,
            dirs=[
                pyhub_path / "ui",
            ],
            tag_formatter="django_components.component_shorthand_formatter",
            # CSS/JS 캐싱
            cache=("dummy" if debug else "locmem"),
            # 템플릿 캐싱은 LRU 메모리에 캐싱 (디폴트: 128)
            # https://django-components.github.io/django-components/latest/reference/settings/#django_components.app_settings.ComponentsSettings.template_cache_size
            # django-components 컴포넌트는 기본적으로 메모리에 캐싱되어있음.
            # 이 LRU 캐싱을 끈다고 해서 매번 파일에서 템플릿 파일을 읽어오는 것은 아님. 컴포넌트 클래스를 등록하는 과정에서 이미 메모리에 로딩.
            # LRU 캐싱은 부가적인 연산에 대한 캐싱. (0: 캐시 끄기, None: 무제한 캐싱)
            # template_cache_size=(0 if debug else 128),
            reload_on_file_change=debug,
            reload_on_template_change=debug,
        ),
        # https://github.com/adamchainz/django-rich
        TEST_RUNNER="django_rich.test.RichRunner",
        FASTMCP_SETTINGS=FastmcpSettings(
            debug=debug,
            instructions=env.str("FASTMCP_INSTRUCTIONS", default=None),
            log_level="DEBUG" if debug else "INFO",
            # Uncomment and configure paths if needed
            # sse_path="/sse",
            # message_path="/messages/",
        ),
    )


def get_databases(base_dir: Path):
    env = Env()

    DEFAULT_DATABASE = f"sqlite:///{ base_dir / 'db.sqlite3'}"
    _databases = {
        "default": env.db("DATABASE_URL", default=DEFAULT_DATABASE),
    }

    for key in os.environ.keys():
        if "_DATABASE_URL" in key:
            db_alias = key.replace("_DATABASE_URL", "").lower()
            parsed_config = env.db_url(key)  # 파싱에 실패하면 빈 사전을 반환합니다.
            if parsed_config:
                _databases[db_alias] = parsed_config

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


def activate_timezone(tzname: Optional[str] = None) -> None:
    if not tzname:
        if hasattr(settings, "USER_DEFAULT_TIME_ZONE"):
            tzname = settings.USER_DEFAULT_TIME_ZONE

    if tzname:
        try:
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        except zoneinfo.ZoneInfoNotFoundError:
            timezone.deactivate()
    else:
        # If no timezone is found in session or default setting, deactivate
        # to use the default (settings.TIME_ZONE)
        timezone.deactivate()


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
        # TODO: django.setup() 이후에 호출 함에도 pyhub.init 로거 설정을 따르지 않음.
        # logging.debug("Loaded django project settings.")

        activate_timezone()

        notify_if_update_available()
