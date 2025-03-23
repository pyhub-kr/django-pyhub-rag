from pathlib import Path

from environ import Env

from pyhub import PromptTemplates, load_envs, load_toml, make_settings

BASE_DIR = Path(__file__).resolve().parent.parent


env = Env()


toml_path = env.str("TOML_PATH", default=None)
if toml_path:
    load_toml(toml_path)


env_path = env.str("ENV_PATH", default=None)
if env_path:
    load_envs(env_path)


PYHUB_SETTINGS = make_settings(base_dir=BASE_DIR, debug_default_value=True)

SECRET_KEY = PYHUB_SETTINGS.SECRET_KEY

ALLOWED_HOSTS = PYHUB_SETTINGS.ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = PYHUB_SETTINGS.CSRF_TRUSTED_ORIGINS


INSTALLED_APPS = [
    *PYHUB_SETTINGS.INSTALLED_APPS,
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

TEMPLATES = PYHUB_SETTINGS.TEMPLATES
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

CACHES = PYHUB_SETTINGS.CACHES

DATABASE_ROUTERS = PYHUB_SETTINGS.DATABASE_ROUTERS
DATABASES = PYHUB_SETTINGS.DATABASES

AUTH_PASSWORD_VALIDATORS = PYHUB_SETTINGS.AUTH_PASSWORD_VALIDATORS

LOGGING = PYHUB_SETTINGS.LOGGING

LANGUAGE_CODE = PYHUB_SETTINGS.LANGUAGE_CODE
TIME_ZONE = PYHUB_SETTINGS.TIME_ZONE
USE_I18N = PYHUB_SETTINGS.USE_I18N
USE_TZ = PYHUB_SETTINGS.USE_TZ

STATIC_URL = PYHUB_SETTINGS.STATIC_URL
STATIC_ROOT = PYHUB_SETTINGS.STATIC_ROOT
STATICFILES_DIRS = PYHUB_SETTINGS.STATICFILES_DIRS
MEDIA_URL = PYHUB_SETTINGS.MEDIA_URL
MEDIA_ROOT = PYHUB_SETTINGS.MEDIA_ROOT

DEFAULT_AUTO_FIELD = PYHUB_SETTINGS.DEFAULT_AUTO_FIELD


#
# api
#

SERVICE_DOMAIN = PYHUB_SETTINGS.SERVICE_DOMAIN

NCP_MAP_CLIENT_ID = PYHUB_SETTINGS.NCP_MAP_CLIENT_ID
NCP_MAP_CLIENT_SECRET = PYHUB_SETTINGS.NCP_MAP_CLIENT_SECRET

PROMPT_TEMPLATES: dict[str, PromptTemplates] = PYHUB_SETTINGS.PROMPT_TEMPLATES
