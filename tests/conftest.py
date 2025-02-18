from django.conf import settings


def pytest_configure():
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "django_db",
                "USER": "djangouser",
                "PASSWORD": "djangopw",
                "HOST": "localhost",
                "PORT": "45432",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "pyhub.rag",
            "test_app",
        ],
        RAG_OPENAI_API_KEY="test-api-key",
        RAG_EMBEDDING_MODEL="text-embedding-3-small",
    )
