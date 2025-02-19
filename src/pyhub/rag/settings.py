import os
from typing import Any

from django.conf import settings

DEFAULTS = {
    "RAG_OPENAI_API_KEY": None,
    "RAG_OPENAI_BASE_URL": "https://api.openai.com/v1",
    "RAG_EMBEDDING_MODEL": "text-embedding-3-small",
    "RAG_EMBEDDING_DIMENSIONS": 1536,
    "RAG_EMBEDDING_MAX_TOKENS_LIMIT": 8191,
}


class RagSettings:
    def __init__(self, defaults) -> None:
        self.defaults = defaults

    def __getattr__(self, attr_name: str) -> Any:
        value = getattr(settings, attr_name, None)

        if value is None and attr_name == "RAG_OPENAI_API_KEY":
            value = getattr(settings, "OPENAI_API_KEY", None)
            if value is None:
                value = os.environ.get("OPENAI_API_KEY", None)

        if value is None:
            try:
                value = self.defaults[attr_name]
            except KeyError:
                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{attr_name}'")
        return value


rag_settings = RagSettings(DEFAULTS)
