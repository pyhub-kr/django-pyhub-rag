from decimal import Decimal
from typing import Union, cast

from pyhub.rag.utils import get_literal_values

from .anthropic import AnthropicLLM
from .base import BaseLLM, SequentialChain
from .google import GoogleLLM
from .ollama import OllamaLLM
from .openai import OpenAILLM
from .types import (
    AnthropicChatModelType,
    GoogleChatModelType,
    GoogleEmbeddingModelType,
    LLMChatModelEnum,
    LLMChatModelType,
    LLMEmbeddingModelEnum,
    LLMEmbeddingModelType,
    LLMModelType,
    LLMVendorType,
    OllamaChatModelType,
    OllamaEmbeddingModelType,
    OpenAIChatModelType,
    OpenAIEmbeddingModelType,
    Price,
    UpstageChatModelType,
    UpstageEmbeddingModelType,
    Usage,
)
from .upstage import UpstageLLM


class LLM:
    MODEL_PRICES = {
        # 2025년 3월 기준
        # https://platform.openai.com/docs/pricing#embeddings
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL: ("0.02", None),
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_LARGE: ("0.13", None),
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_004: ("0", None),  # 가격 명시 없음.
        # https://platform.openai.com/docs/pricing#latest-models
        LLMChatModelEnum.GPT_4O: ("2.5", "10.0"),
        LLMChatModelEnum.GPT_4O_MINI: ("0.15", "0.60"),
        LLMChatModelEnum.O1: ("15", "60.00"),
        # LLMChatModelEnum.O3_MINI: ("1.10", "4.40"),
        LLMChatModelEnum.O1_MINI: ("1.10", "4.40"),
        # https://www.anthropic.com/pricing#anthropic-api
        # LLMChatModelEnum.CLAUDE_OPUS_4_LATEST: ("15", "75"),
        # LLMChatModelEnum.CLAUDE_SONNET_4_20250514: ("3", "15"),
        LLMChatModelEnum.CLAUDE_SONNET_3_7_LATEST: ("3", "15"),
        LLMChatModelEnum.CLAUDE_HAIKU_3_5_LATEST: ("0.80", "4"),
        LLMChatModelEnum.CLAUDE_OPUS_3_LATEST: ("15", "75"),
        # https://www.upstage.ai/pricing
        LLMChatModelEnum.UPSTAGE_SOLAR_MINI: ("0.15", "0.15"),  # TODO: 가격 확인
        LLMChatModelEnum.UPSTAGE_SOLAR_PRO: ("0.25", "0.15"),
        # https://ai.google.dev/gemini-api/docs/pricing?hl=ko
        LLMChatModelEnum.GEMINI_2_0_FLASH: ("0.10", "0.40"),
        LLMChatModelEnum.GEMINI_2_0_FLASH_LITE: ("0.075", "0.30"),
        LLMChatModelEnum.GEMINI_1_5_FLASH: ("0.075", "0.30"),  # 128,000 토큰 초과 시에는 *2
        LLMChatModelEnum.GEMINI_1_5_FLASH_8B: ("0.0375", "0.15"),  # 128,000 토큰 초과 시에는 *2
        LLMChatModelEnum.GEMINI_1_5_PRO: ("1.25", "5.0"),  # 128,000 토큰 초과 시에는 *2
    }

    @classmethod
    def get_vendor_from_model(cls, model: LLMModelType) -> LLMVendorType:
        """주어진 model로부터 해당하는 vendor를 찾아 반환합니다."""
        if model in get_literal_values(OpenAIChatModelType, OpenAIEmbeddingModelType):
            return "openai"
        elif model in get_literal_values(UpstageChatModelType, UpstageEmbeddingModelType):
            return "upstage"
        elif model in get_literal_values(AnthropicChatModelType):
            return "anthropic"
        elif model in get_literal_values(GoogleChatModelType, GoogleEmbeddingModelType):
            return "google"
        elif model in get_literal_values(OllamaChatModelType, OllamaEmbeddingModelType):
            return "ollama"
        else:
            raise ValueError(f"Unknown model: {model}")

    @classmethod
    def create(
        cls,
        model: LLMModelType,
        **kwargs,
    ) -> "BaseLLM":
        vendor = cls.get_vendor_from_model(model)

        #
        # chat
        #
        if model in get_literal_values(LLMChatModelType):
            if vendor == "openai":
                return OpenAILLM(model=cast(OpenAIChatModelType, model), **kwargs)
            elif vendor == "upstage":
                return UpstageLLM(model=cast(UpstageChatModelType, model), **kwargs)
            elif vendor == "anthropic":
                return AnthropicLLM(model=cast(AnthropicChatModelType, model), **kwargs)
            elif vendor == "google":
                return GoogleLLM(model=cast(GoogleChatModelType, model), **kwargs)
            elif vendor == "ollama":
                if "max_tokens" in kwargs:
                    del kwargs["max_tokens"]
                return OllamaLLM(model=cast(OllamaChatModelType, model), **kwargs)

        #
        # embedding
        #
        elif model in get_literal_values(LLMEmbeddingModelType):
            if vendor == "openai":
                return OpenAILLM(
                    embedding_model=cast(OpenAIEmbeddingModelType, model),
                    **kwargs,
                )
            elif vendor == "upstage":
                return UpstageLLM(
                    embedding_model=cast(UpstageEmbeddingModelType, model),
                    **kwargs,
                )
            elif vendor == "google":
                return GoogleLLM(
                    embedding_model=cast(GoogleEmbeddingModelType, model),
                    **kwargs,
                )
            elif vendor == "ollama":
                if "max_tokens" in kwargs:
                    del kwargs["max_tokens"]
                return OllamaLLM(
                    embedding_model=cast(OllamaEmbeddingModelType, model),
                    **kwargs,
                )

        raise ValueError(f"Invalid model name: {model}")

    @classmethod
    def get_price(cls, model: Union[LLMChatModelType, LLMEmbeddingModelType], usage: Usage) -> Price:
        try:
            input_per_1m, output_per_1m = cls.MODEL_PRICES[model]
        except KeyError:
            return Price()

        if input_per_1m:
            input_per_1m = Decimal(input_per_1m)
            input_usd = (Decimal(usage.input) * input_per_1m) / Decimal("1_000_000")
        else:
            input_usd = None

        if output_per_1m:
            output_per_1m = Decimal(output_per_1m)
            output_usd = (Decimal(usage.input) * output_per_1m) / Decimal("1_000_000")
        else:
            output_usd = None

        return Price(input_usd=input_usd, output_usd=output_usd)


__all__ = ["LLM", "BaseLLM", "SequentialChain", "AnthropicLLM", "GoogleLLM", "OllamaLLM", "OpenAILLM", "UpstageLLM"]
