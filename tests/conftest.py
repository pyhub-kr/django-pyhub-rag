from django.conf import settings
from environ import Env


def pytest_configure():

    env = Env()
    env.DB_SCHEMES["sqlite"] = "pyhub.db.backends.sqlite3"

    settings.configure(
        DATABASES={
            "default": env.db("DATABASE_URL", default="sqlite://:memory:"),
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "pyhub.rag",
            "test_app",
        ],
        CACHES={
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
        },
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
        RAG_OPENAI_API_KEY=None,
        LOGGING={
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
                    "level": "DEBUG",
                },
            },
        },
    )

    # DB 생성 전에 serialize_db_to_string 메서드 오버라이드
    # pytest.mark.django_db는 기본적으로 모든 임포트된 모델에 대해 2000건의 데이터를 메모리에 로드합니다.
    # 하지만 현재 테스트에서는 데이터베이스 벤더별로 다른 모델을 사용하므로,
    # 일부 모델은 테이블이 생성되지 않아 데이터 로딩 시 오류가 발생합니다.
    # 이를 방지하기 위해 데이터 로딩 기능을 비활성화합니다.

    from django.db.backends.base.creation import BaseDatabaseCreation

    BaseDatabaseCreation.serialize_db_to_string = lambda self: ""
