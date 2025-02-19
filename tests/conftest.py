from django.conf import settings
from environ import Env


def pytest_configure():

    env = Env()

    settings.configure(
        DATABASES={
            "default": env.db(
                "DATABASE_URL",
                default="postgresql://djangouser:djangopw@localhost:5432/django_db",
            ),
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
