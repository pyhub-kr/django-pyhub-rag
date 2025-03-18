from dataclasses import asdict, dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Literal, TypeAlias, Union

from anthropic.types import ModelParam as AnthropicChatModelType
from django.core.files import File
from openai.types import ChatModel as OpenAIChatModelType
from typing_extensions import Optional

#
# Vendor
#

LLMVendor: TypeAlias = Literal["openai", "anthropic", "google", "ollama"]

#
# Language
#

LanguageType: TypeAlias = Union[
    Literal["korean", "english", "japanese", "chinese"],
    str,
]

#
# Embedding
#

OpenAIEmbeddingModelType: TypeAlias = Literal[
    "text-embedding-ada-002",  # 1536 차원
    "text-embedding-3-small",  # 1536 차원
    "text-embedding-3-large",  # 3072 차원
]

# https://console.upstage.ai/docs/capabilities/embeddings
UpstageEmbeddingModelType: TypeAlias = Literal[
    "embedding-query",  # 검색어 목적 (4096차원)
    "embedding-passage",  # 문서의 일부, 문장 또는 긴 텍스트 목적 (4096차원)
]


OllamaEmbeddingModelType: TypeAlias = Union[
    Literal[
        "nomic-embed-text",  # 768 차원
        "avr/sfr-embedding-mistral",  # 4096 차원
    ],
    str,
]

# https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings?hl=ko
GoogleEmbeddingModelType: TypeAlias = Literal["text-embedding-004"]  # 768 차원

LLMEmbeddingModelType = Union[
    OpenAIEmbeddingModelType, UpstageEmbeddingModelType, OllamaEmbeddingModelType, GoogleEmbeddingModelType
]


#
# Chat
#

OpenAIChatModelType  # noqa

AnthropicChatModelType  # noqa

# https://console.upstage.ai/docs/capabilities/chat
UpstageChatModelType: TypeAlias = Union[
    Literal[
        "solar-pro",
        "solar-mini",
    ]
]

OllamaChatModelType: TypeAlias = Union[
    Literal[
        # tools, 70b : https://ollama.com/library/llama3.3
        "llama3.3",
        "llama3.3:70b",
        # tools, 1b, 3b : https://ollama.com/library/llama3.2
        "llama3.2",
        "llama3.2:1b",
        "llama3.2:3b",
        # tools, 8b, 70b, 405b : https://ollama.com/library/llama3.1
        "llama3.1",
        "llama3.1:8b",
        "llama3.1:70b",
        "llama3.1:405b",
        # tools, 7b : https://ollama.com/library/mistral
        "mistral",
        "mistral:7b",
        # tools, 0.5b, 1.5b, 7b, 72b : https://ollama.com/library/qwen2
        "qwen2",
        "qwen2:0.5b",
        "qwen2:1.5b",
        "qwen2:7b",
        "qwen2:72b",
        # vision, 1b, 4b, 12b, 27b : https://ollama.com/library/gemma3
        "gemma3",
        "gemma3:1b",
        "gemma3:4b",
        "gemma3:12b",
        "gemma3:27b",
    ],
    str,
]

# https://ai.google.dev/gemini-api/docs/models/gemini?hl=ko
GoogleChatModelType: TypeAlias = Union[
    Literal[
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ],
]


LLMChatModelType: TypeAlias = Union[
    OpenAIChatModelType, AnthropicChatModelType, UpstageChatModelType, GoogleChatModelType, OllamaChatModelType
]


#
# Groundedness Check
#

# https://console.upstage.ai/docs/capabilities/groundedness-check#available-models
UpstageGroundednessCheckModel: TypeAlias = Literal["groundedness-check",]


#
# Types
#


@dataclass
class GroundednessCheck:
    is_grounded: Optional[bool] = None  # grounded (True), notGrounded (False), notSure (None)
    usage: Optional["Usage"] = None

    def __bool__(self):
        return self.is_grounded


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "function"]
    content: str
    files: Optional[list[Union[str, Path, File]]] = None

    def __iter__(self):
        for key, value in self.to_dict().items():
            yield key, value

    def to_dict(self) -> dict:
        d = asdict(self)
        del d["files"]  # LLM API에서는 없는 속성이기에 제거
        return d


@dataclass
class Usage:
    input: int = 0
    output: int = 0

    def __add__(self, other):
        if isinstance(other, Usage):
            return Usage(input=self.input + other.input, output=self.output + other.output)
        return NotImplemented


@dataclass
class Price:
    input_usd: Optional[Decimal] = None
    output_usd: Optional[Decimal] = None
    usd: Optional[Decimal] = None
    krw: Optional[Decimal] = None
    rate_usd: int = 1500

    def __post_init__(self):
        self.input_usd = self.input_usd or Decimal("0")
        self.output_usd = self.output_usd or Decimal("0")

        if not isinstance(self.input_usd, Decimal):
            self.input_usd = Decimal(str(self.input_usd))
        if not isinstance(self.output_usd, Decimal):
            self.output_usd = Decimal(str(self.output_usd))
        if self.usd is not None and not isinstance(self.usd, Decimal):
            self.usd = Decimal(str(self.usd))
        if self.krw is not None and not isinstance(self.krw, Decimal):
            self.krw = Decimal(str(self.krw))

        if self.usd is None:
            self.usd = self.input_usd + self.output_usd

        if self.krw is None:
            self.krw = self.usd * Decimal(self.rate_usd)


@dataclass
class Reply:
    text: str = ""
    usage: Optional[Usage] = None

    def __str__(self) -> str:
        return self.text

    def __format__(self, format_spec: str) -> str:
        return format(self.text, format_spec)


@dataclass
class ChainReply:
    values: dict[str, Any] = field(default_factory=dict)
    reply_list: list[Reply] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.reply_list)

    @property
    def text(self) -> str:
        try:
            return self.reply_list[-1].text
        except IndexError:
            return ""

    @property
    def usage(self) -> Optional[Usage]:
        try:
            return self.reply_list[-1].usage
        except IndexError:
            return None

    def __getitem__(self, key) -> Any:
        return self.values.get(key)


@dataclass
class Embed:
    array: list[float]  # noqa
    usage: Optional[Usage] = None

    def __iter__(self):
        return iter(self.array)

    def __len__(self):
        return len(self.array)

    def __getitem__(self, index):
        return self.array[index]

    def __str__(self):
        return str(self.array)


@dataclass
class EmbedList:
    arrays: list[Embed]  # noqa
    usage: Optional[Usage] = None

    def __iter__(self):
        return iter(self.arrays)

    def __len__(self):
        return len(self.arrays)

    def __getitem__(self, index):
        return self.arrays[index]

    def __str__(self):
        return str(self.arrays)


class LanguageEnum(str, Enum):
    KOREAN = "korean"
    ENGLISH = "english"
    JAPANESE = "japanese"
    CHINESE = "chinese"


class LLMVendorEnum(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    UPSTAGE = "upstage"
    OLLAMA = "ollama"


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
    # google
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite"
    GEMINI_1_5_FLASH = "gemini-1.5-flash"
    GEMINI_1_5_FLASH_8B = "gemini-1.5-flash-8b"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    # upstage
    UPSTAGE_SOLAR_PRO = "solar-pro"
    UPSTAGE_SOLAR_MINI = "solar-mini"
    # ollama
    LLAMA_3_3 = "llama3.3"
    LLAMA_3_3_70B = "llama3.3:70b"
    LLAMA_3_2 = "llama3.2"
    LLAMA_3_2_1B = "llama3.2:1b"
    LLAMA_3_2_3B = "llama3.2:3b"
    LLAMA_3_1 = "llama3.1"
    LLAMA_3_1_8B = "llama3.1_8B"
    LLAMA_3_1_70B = "llama3.1:70B"
    LLAMA_3_1_405B = "llama3.1:405B"
    MISTRAL = "mistral"
    MISTRAL_7B = "mistral:7b"
    QWEN2 = "qwen2"
    QWEN2_0_5B = "qwen2:0.5b"
    QWEN2_1_5B = "qwen2:1.5b"
    QWEN2_7B = "qwen2:7b"
    QWEN2_72B = "qwen2:72b"
    GEMMA3 = "gemma3"
    GEMMA3_1B = "gemma3:1b"
    GEMMA3_4B = "gemma3:4b"
    GEMMA3_12B = "gemma3:12b"
    GEMMA3_27B = "gemma3:27b"
