from enum import Enum


class EmbeddingDimensionsEnum(str, Enum):
    D_768 = "768"
    D_1536 = "1536"
    D_3072 = "3072"


class LLMEmbeddingModelEnum(str, Enum):
    TEXT_EMBEDDING_ADA_02 = "text-embedding-ada-002"
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    TEXT_EMBEDDING_004 = "text-embedding-004"


class LLMChatModelEnum(str, Enum):
    # openai
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    CHATGPT_4O_LATEST = "chatgpt-4o-latest"
    O1 = "o1"
    O1_MINI = "o1-mini"
    O3_MINI = "o3-mini"
    # anthropic
    CLAUDE_3_7_SONNET_LATEST = "claude-3-7-sonnet-latest"
    CLAUDE_3_5_HAIKU_LATEST = "claude-3-5-haiku-latest"
    CLAUDE_3_5_SONNET_LATEST = "claude-3-5-sonnet-latest"
    CLAUDE_3_OPUS_LATEST = "claude-3-opus-latest"
    # solar
    UPSTAGE_SOLAR_PRO = "solar-pro"
    UPSTAGE_SOLAR_MINI = "solar-mini"
    # google
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_FLASH_8B = "gemini-1.5-flash-8b"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
