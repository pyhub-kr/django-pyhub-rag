import os
from typing import Any, Optional, Union

from django.conf import settings as proj_settings
from django.core.exceptions import ImproperlyConfigured

from pyhub.llm.types import LLMEmbeddingModelType

DEFAULTS = {
    "openai_base_url": "https://api.openai.com/v1",
    "upstage_base_url": "https://api.upstage.ai/v1/solar",
    "ollama_base_url": "http://localhost:11434",
    "embedding_model": "text-embedding-3-small",
    "embedding_dimensions": 1536,
    "embedding_max_tokens_limit": 8191,
}


class RagSettings:
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        upstage_api_key: Optional[str] = None,
        upstage_base_url: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        embedding_model: Optional[LLMEmbeddingModelType] = None,
        embedding_dimensions: Optional[int] = None,
        embedding_max_tokens_limit: Optional[int] = None,
    ):
        self.init_kwargs = {
            "openai_api_key": openai_api_key,
            "openai_base_url": openai_base_url,
            "upstage_api_key": upstage_api_key,
            "upstage_base_url": upstage_base_url,
            "anthropic_api_key": anthropic_api_key,
            "google_api_key": google_api_key,
            "ollama_base_url": ollama_base_url,
            "embedding_model": embedding_model,
            "embedding_dimensions": embedding_dimensions,
            "embedding_max_tokens_limit": embedding_max_tokens_limit,
        }

        # 생성자에서 모든 값 초기화
        self.openai_api_key = openai_api_key
        self.openai_base_url = openai_base_url
        self.upstage_api_key = upstage_api_key
        self.upstage_base_url = upstage_base_url
        self.anthropic_api_key = anthropic_api_key
        self.google_api_key = google_api_key
        self.ollama_base_url = ollama_base_url
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.embedding_max_tokens_limit = embedding_max_tokens_limit
        self.reload()

    def reload(self):
        for k, v in self.init_kwargs.items():
            setattr(self, k, v)

        # 2. 환경 변수나 Django 설정에서 값 가져오기
        # API 키들은 특별 처리 (RAG_ 접두사 없는 버전도 확인)
        if self.openai_api_key is None:
            self.openai_api_key = self.get_proj_settings_or_environ(("RAG_OPENAI_API_KEY", "OPENAI_API_KEY"))

        if self.upstage_api_key is None:
            self.upstage_api_key = self.get_proj_settings_or_environ(("RAG_UPSTAGE_API_KEY", "UPSTAGE_API_KEY"))

        if self.anthropic_api_key is None:
            self.anthropic_api_key = self.get_proj_settings_or_environ(("RAG_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"))

        if self.google_api_key is None:
            self.google_api_key = self.get_proj_settings_or_environ(("RAG_GOOGLE_API_KEY", "GOOGLE_API_KEY"))

        if self.openai_base_url is None:
            self.openai_base_url = (
                self.get_proj_settings_or_environ(("RAG_OPENAI_BASE_URL", "OPENAI_BASE_URL"))
                or DEFAULTS["openai_base_url"]
            )

        if self.upstage_base_url is None:
            self.upstage_base_url = (
                self.get_proj_settings_or_environ(("RAG_UPSTAGE_BASE_URL", "UPSTAGE_BASE_URL"))
                or DEFAULTS["upstage_base_url"]
            )

        if self.ollama_base_url is None:
            self.ollama_base_url = (
                self.get_proj_settings_or_environ(("RAG_OLLAMA_BASE_URL", "OLLAMA_BASE_URL"))
                or DEFAULTS["ollama_base_url"]
            )

        if self.embedding_model is None:
            self.embedding_model = (
                self.get_proj_settings_or_environ(("RAG_EMBEDDING_MODEL", "EMBEDDING_MODEL"))
                or DEFAULTS["embedding_model"]
            )

        if self.embedding_dimensions is None:
            embedding_dim_str = self.get_proj_settings_or_environ(("RAG_EMBEDDING_DIMENSIONS", "EMBEDDING_DIMENSIONS"))
            self.embedding_dimensions = (
                int(embedding_dim_str) if embedding_dim_str else DEFAULTS["embedding_dimensions"]
            )

        if self.embedding_max_tokens_limit is None:
            tokens_limit_str = self.get_proj_settings_or_environ("RAG_EMBEDDING_MAX_TOKENS_LIMIT")
            self.embedding_max_tokens_limit = (
                int(tokens_limit_str) if tokens_limit_str else DEFAULTS["embedding_max_tokens_limit"]
            )

    def get_proj_settings_or_environ(self, attr_name: Union[str, tuple[str, ...]]) -> Any:
        if isinstance(attr_name, str):
            attr_names = (attr_name,)
        else:
            attr_names = attr_name

        for name in attr_names:
            # 장고 프로젝트가 로딩되지 않은 상황에서는 ImproperlyConfigured 예외가 발생합니다.
            # 장고 프로젝트가 없는 상황에서도 pyhub.llm 팩키지를 사용할 수 있습니다.
            try:
                value = getattr(proj_settings, name, None)
                if value is not None:
                    return value
            except ImproperlyConfigured:
                pass

            value = os.environ.get(name, None)
            if value is not None:
                return value

        return None


rag_settings = RagSettings()
