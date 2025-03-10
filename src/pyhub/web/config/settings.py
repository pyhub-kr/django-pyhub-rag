from pathlib import Path

from environ import Env

BASE_DIR = Path(__file__).resolve().parent.parent


env = Env()

env_path = env.str("ENV_PATH", default=None)
if env_path:
    env.read_env(env_path, overwrite=True)


SECRET_KEY = env.str(
    "SECRET_KEY",
    default="django-insecure-2%6ln@_fnpi!=ivjk(=)e7nx!7abp9d2e3f-+!*o=4s(bd1ynf",
)

DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", ".ngrok-free.app"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


INSTALLED_APPS = [
    # "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    # "django.contrib.messages",
    # "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
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
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASE_ROUTERS = ["pyhub.routers.Router"]

DEFAULT_DATABASE = f"sqlite:///{ BASE_DIR / 'db.sqlite3'}"

DATABASES = {
    "default": env.db("DATABASE_URL", default=DEFAULT_DATABASE),
}

for db_name in DATABASES:
    if DATABASES[db_name]["ENGINE"] == "django.db.backends.sqlite3":
        DATABASES[db_name]["ENGINE"] = "pyhub.db.backends.sqlite3"

        DATABASES[db_name].setdefault("OPTIONS", {})

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

        # https://gcollazo.com/optimal-sqlite-settings-for-django/
        DATABASES[db_name]["OPTIONS"].update(
            {
                "init_command": (
                    f"PRAGMA foreign_keys={PRAGMA_FOREIGN_KEYS};"
                    f"PRAGMA journal_mode = {PRAGMA_JOURNAL_MODE};"
                    f"PRAGMA synchronous = {PRAGMA_SYNCHRONOUS};"
                    f"PRAGMA busy_timeout = {PRAGMA_BUSY_TIMEOUT};"
                    f"PRAGMA temp_store = {PRAGMA_TEMP_STORE};"
                    f"PRAGMA mmap_size = {PRAGMA_MMAP_SIZE};"
                    f"PRAGMA journal_size_limit = {PRAGMA_JOURNAL_SIZE_LIMIT};"
                    f"PRAGMA cache_size = {PRAGMA_CACHE_SIZE};"
                ),
                "transaction_mode": PRAGMA_TRANSACTION_MODE,
            }
        )


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
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
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = env.str("LANGUAGE_CODE", default="ko-kr")

TIME_ZONE = env.str("TIME_ZONE", default="UTC")

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


#
# api
#

SERVICE_DOMAIN = env.str("SERVICE_DOMAIN", default=None)

NCP_MAP_CLIENT_ID = env.str("NCP_MAP_CLIENT_ID", default=None)
NCP_MAP_CLIENT_SECRET = env.str("NCP_MAP_CLIENT_SECRET", default=None)
