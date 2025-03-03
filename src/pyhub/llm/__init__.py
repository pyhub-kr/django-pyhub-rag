from typing import cast

from .anthropic import AnthropicLLM
from .base import BaseLLM
from .google import GoogleLLM
from .openai import OpenAILLM
from .types import AnthropicChatModel, GoogleChatModel, LLMChatModel, OpenAIChatModel


class LLM:

    @classmethod
    def create(cls, model: LLMChatModel, **kwargs) -> "BaseLLM":
        """Factory method to create appropriate LLM instance based on model name"""
        if "claude" in model.lower():
            return AnthropicLLM(model=cast(AnthropicChatModel, model), **kwargs)
        elif "gemini" in model.lower():
            return GoogleLLM(model=cast(GoogleChatModel, model), **kwargs)
        else:  # Default to OpenAI
            return OpenAILLM(model=cast(OpenAIChatModel, model), **kwargs)


__all__ = ["LLM", "BaseLLM", "AnthropicLLM", "GoogleLLM", "OpenAILLM"]
