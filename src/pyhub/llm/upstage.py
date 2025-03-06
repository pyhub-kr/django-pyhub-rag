from typing import Optional

from ..rag.settings import rag_settings
from .base import BaseLLM
from .openai import OpenAIMixin
from .types import Message, UpstageChatModel, UpstageEmbeddingModel


class UpstageLLM(OpenAIMixin, BaseLLM):
    EMBEDDING_DIMENSIONS = {
        "embedding-query": 4096,
        "embedding-passage": 4096,
    }

    def __init__(
        self,
        model: UpstageChatModel = "solar-mini",
        embedding_model: UpstageEmbeddingModel = "embedding-query",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[list[Message]] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(
            model=model,
            embedding_model=embedding_model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            initial_messages=initial_messages,
            api_key=api_key or rag_settings.upstage_api_key,
        )

        self.base_url = base_url or rag_settings.upstage_base_url
