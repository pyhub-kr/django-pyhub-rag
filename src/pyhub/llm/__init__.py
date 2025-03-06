from decimal import Decimal
from typing import Union, cast

from ..rag.utils import get_literal_values
from .anthropic import AnthropicLLM
from .base import BaseLLM
from .enum import LLMChatModelEnum, LLMEmbeddingModelEnum
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
    Price,
    UpstageChatModel,
    Usage,
)


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
        LLMChatModelEnum.O3_MINI: ("1.10", "4.40"),
        LLMChatModelEnum.O1_MINI: ("1.10", "4.40"),
        # https://www.anthropic.com/pricing#anthropic-api
        LLMChatModelEnum.CLAUDE_3_7_SONNET_LATEST: ("3", "15"),
        LLMChatModelEnum.CLAUDE_3_5_HAIKU_LATEST: ("0.80", "4"),
        LLMChatModelEnum.CLAUDE_3_OPUS_LATEST: ("15", "75"),
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
    def create(cls, model: Union[LLMChatModel, LLMEmbeddingModel], **kwargs) -> "BaseLLM":
        if model in get_literal_values(AnthropicChatModel):
            return AnthropicLLM(model=cast(AnthropicChatModel, model), **kwargs)
        elif model in get_literal_values(GoogleChatModel):
            return GoogleLLM(model=cast(GoogleChatModel, model), **kwargs)
        elif model in get_literal_values(OpenAIChatModel, UpstageChatModel):
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

    @classmethod
    def get_price(cls, model: Union[LLMChatModel, LLMEmbeddingModel], usage: Usage) -> Price:
        input_per_1m, output_per_1m = cls.MODEL_PRICES[model]

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


__all__ = ["LLM", "BaseLLM", "AnthropicLLM", "GoogleLLM", "OpenAILLM"]
