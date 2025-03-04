from typing import Union, cast

from ..rag.utils import get_literal_values
from .anthropic import AnthropicLLM
from .base import BaseLLM
from .google import GoogleLLM
from .openai import OpenAILLM
from .types import (
    AnthropicChatModel,
    GoogleChatModel,
    GoogleEmbeddingModel,
    LLMChatModel,
    LLMEmbeddingModel,
    OpenAIChatModel,
    OpenAIEmbeddingModel,
)


class LLM:

    @classmethod
    def create(cls, model: Union[LLMChatModel, LLMEmbeddingModel], **kwargs) -> "BaseLLM":
        if model in get_literal_values(AnthropicChatModel):
            return AnthropicLLM(model=cast(AnthropicChatModel, model), **kwargs)
        elif model in get_literal_values(GoogleChatModel):
            return GoogleLLM(model=cast(GoogleChatModel, model), **kwargs)
        elif model in get_literal_values(OpenAIChatModel):
            return OpenAILLM(model=cast(OpenAIChatModel, model), **kwargs)
        elif model in get_literal_values(OpenAIEmbeddingModel):
            return OpenAILLM(
                embedding_model=cast(OpenAIEmbeddingModel, model),
                **kwargs,
            )
        elif model in get_literal_values(GoogleEmbeddingModel):
            return GoogleLLM(
                embedding_model=cast(GoogleEmbeddingModel, model),
                **kwargs,
            )
        else:
            raise ValueError(f"Invalid model name: {model}")


__all__ = ["LLM", "BaseLLM", "AnthropicLLM", "GoogleLLM", "OpenAILLM"]
