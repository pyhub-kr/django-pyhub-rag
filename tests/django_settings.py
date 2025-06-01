"""
Django settings for PyCharm test runner.
This configuration excludes vector-related apps to avoid sqlite-vec dependency.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-test-key-only-for-testing"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition - minimal apps to avoid vector dependencies
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "pyhub.core",
    "pyhub.llm",
    "pyhub.parser",
]

MIDDLEWARE = []

ROOT_URLCONF = None

TEMPLATES = [
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
]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "pyhub_cache",
    },
    "upstage": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "pyhub_upstage",
    },
    "openai": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "pyhub_openai",
    },
    "anthropic": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "pyhub_anthropic",
    },
    "google": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "pyhub_google",
    },
    "ollama": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "pyhub_ollama",
    },
}

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# RAG settings
RAG_OPENAI_API_KEY = None

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "INFO",  # Less verbose for tests
        },
    },
}
