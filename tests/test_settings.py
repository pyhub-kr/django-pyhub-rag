import os

import pytest
from django.conf import settings

from pyhub.rag.settings import rag_settings


def test_rag_settings_defaults(monkeypatch):
    """
    Django 설정에서 값을 가져오는지 테스트하고
    설정이 제공되지 않은 경우 기본값으로 대체되는지 확인합니다.
    또한 충돌하는 환경 변수가 없는지 확인합니다.
    """

    # 간섭을 방지하기 위해 환경에서 OPENAI_API_KEY를 제거합니다.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # 이 값들은 tests/conftest.py에서 Django 설정을 통해 설정됩니다.
    assert settings.RAG_OPENAI_API_KEY == "test-api-key"
    assert settings.RAG_EMBEDDING_MODEL == "text-embedding-3-small"

    # Django 설정에 명시적으로 정의되지 않은 설정의 경우, rag_settings는 기본값을 사용해야 합니다.
    assert rag_settings.RAG_OPENAI_BASE_URL == "https://api.openai.com/v1"
    assert rag_settings.RAG_EMBEDDING_DIMENSIONS == 1536
    assert rag_settings.RAG_EMBEDDING_MAX_TOKENS_LIMIT == 8191


def test_rag_settings_env_override(monkeypatch):
    """
    Django 설정에 RAG_OPENAI_API_KEY가 설정되지 않은 경우,
    rag_settings가 OPENAI_API_KEY 환경변수에서 값을 가져오는지 테스트합니다.
    환경 변수가 올바르게 설정되었는지 확인합니다.
    """
    # Django 설정을 None으로 설정하여 설정이 없는 상황을 시뮬레이션합니다.
    monkeypatch.setattr(settings, "RAG_OPENAI_API_KEY", None)

    # 환경 변수를 테스트 값으로 설정합니다.
    test_env_api_key = "env-api-key"
    monkeypatch.setenv("OPENAI_API_KEY", test_env_api_key)

    # 환경 변수가 올바르게 설정되었는지 확인합니다.
    assert os.environ.get("OPENAI_API_KEY") == test_env_api_key

    # rag_settings가 환경변수에서 값을 가져오는지 확인합니다.
    assert rag_settings.RAG_OPENAI_API_KEY == test_env_api_key


def test_rag_settings_openai_api_key_fallback(monkeypatch):
    """
    RAG_OPENAI_API_KEY 환경변수가 없고 OPENAI_API_KEY 환경변수만 있을 때,
    rag_settings.RAG_OPENAI_API_KEY가 OPENAI_API_KEY 값을 사용하는지 테스트합니다.
    """
    # Django 설정에서 RAG_OPENAI_API_KEY를 제거합니다
    monkeypatch.setattr(settings, "RAG_OPENAI_API_KEY", None)

    # OPENAI_API_KEY 환경변수만 설정합니다
    test_openai_api_key = "test-openai-key"
    monkeypatch.setenv("OPENAI_API_KEY", test_openai_api_key)

    # rag_settings가 OPENAI_API_KEY 환경변수 값을 사용하는지 확인합니다
    assert rag_settings.RAG_OPENAI_API_KEY == test_openai_api_key


def test_rag_settings_invalid_attribute():
    """
    rag_settings에서 존재하지 않는 속성에 접근할 때 AttributeError가 발생하는지 테스트합니다.
    """
    with pytest.raises(AttributeError):
        _ = rag_settings.NON_EXISTENT_ATTRIBUTE
