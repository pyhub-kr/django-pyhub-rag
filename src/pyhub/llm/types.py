from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, TypeAlias, Union

from anthropic.types import ModelParam as AnthropicChatModelType
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db.models import TextChoices
from openai.types import ChatModel as OpenAIChatModelType
from typing_extensions import Optional

from pyhub.core.utils import enum_to_flatten_set, type_to_flatten_set

#
# Vendor
#

LLMVendorType: TypeAlias = Literal["openai", "anthropic", "google", "upstage", "ollama"]

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


LLMModelType = Union[LLMChatModelType, LLMEmbeddingModelType]

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

    def __bool__(self):
        if self.input == 0 and self.output == 0:
            return False
        return True


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


class LanguageEnum(TextChoices):
    KOREAN = "korean"
    ENGLISH = "english"
    JAPANESE = "japanese"
    CHINESE = "chinese"


class LLMVendorEnum(TextChoices):
    OPENAI = "openai", "OpenAI"
    ANTHROPIC = "anthropic", "Anthropic"
    GOOGLE = "google", "Google"
    UPSTAGE = "upstage", "Upstage"
    OLLAMA = "ollama", "Ollama"


class EmbeddingDimensionsEnum(TextChoices):
    D_768 = "768"
    D_1536 = "1536"
    D_3072 = "3072"


class LLMEmbeddingModelEnum(TextChoices):
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small", "text-embedding-3-small"
    TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large", "text-embedding-3-large"
    TEXT_EMBEDDING_004 = "text-embedding-004", "text-embedding-004"
    TEXT_EMBEDDING_ADA_02 = "text-embedding-ada-002", "text-embedding-ada-002"


class OpenAIChatModelEnum(TextChoices):
    GPT_4O = "gpt-4o", "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini", "gpt-4o-mini"
    CHATGPT_4O_LATEST = "chatgpt-4o-latest", "chatgpt-4o-latest"
    O1 = "o1", "o1"
    O1_MINI = "o1-mini", "o1-mini"
    # O3_MINI = "o3-mini", "o3-mini"


class AnthropicChatModelEnum(TextChoices):
    CLAUDE_3_7_SONNET_LATEST = "claude-3-7-sonnet-latest", "claude-3-7-sonnet-latest"
    CLAUDE_3_5_HAIKU_LATEST = "claude-3-5-haiku-latest", "claude-3-5-haiku-latest"
    CLAUDE_3_5_SONNET_LATEST = "claude-3-5-sonnet-latest", "claude-3-5-sonnet-latest"
    CLAUDE_3_OPUS_LATEST = "claude-3-opus-latest", "claude-3-opus-latest"


class UpstageChatModelEnum(TextChoices):
    UPSTAGE_SOLAR_PRO = "solar-pro", "solar-pro"
    UPSTAGE_SOLAR_MINI = "solar-mini", "solar-mini"


class GoogleChatModelEnum(TextChoices):
    GEMINI_2_0_FLASH = "gemini-2.0-flash", "gemini-2.0-flash"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite", "gemini-2.0-flash-lite"
    GEMINI_1_5_FLASH = "gemini-1.5-flash", "gemini-1.5-flash"
    GEMINI_1_5_FLASH_8B = "gemini-1.5-flash-8b", "gemini-1.5-flash-8b"
    GEMINI_1_5_PRO = "gemini-1.5-pro", "gemini-1.5-pro"


class OllamaChatModelEnum(TextChoices):
    LLAMA_3_3 = "llama3.3", "llama3.3"
    LLAMA_3_3_70B = "llama3.3:70b", "llama3.3:70b"
    LLAMA_3_2 = "llama3.2", "llama3.2"
    LLAMA_3_2_1B = "llama3.2:1b", "llama3.2:1b"
    LLAMA_3_2_3B = "llama3.2:3b", "llama3.2:3b"
    LLAMA_3_1 = "llama3.1", "llama3.1"
    LLAMA_3_1_8B = "llama3.1:8b", "llama3.1:8b"
    LLAMA_3_1_70B = "llama3.1:70b", "llama3.1:70b"
    LLAMA_3_1_405B = "llama3.1:405b", "llama3.1:405b"
    MISTRAL = "mistral", "mistral"
    MISTRAL_7B = "mistral:7b", "mistral:7b"
    QWEN2 = "qwen2", "qwen2"
    QWEN2_0_5B = "qwen2:0.5b", "qwen2:0.5b"
    QWEN2_1_5B = "qwen2:1.5b", "qwen2:1.5b"
    QWEN2_7B = "qwen2:7b", "qwen2:7b"
    QWEN2_72B = "qwen2:72b", "qwen2:72b"
    GEMMA3 = "gemma3", "gemma3"
    GEMMA3_1B = "gemma3:1b", "gemma3:1b"
    GEMMA3_4B = "gemma3:4b", "gemma3:4b"
    GEMMA3_12B = "gemma3:12b", "gemma3:12b"
    GEMMA3_27B = "gemma3:27b", "gemma3:27b"


# enum은 상속을 지원하지 않습니다.
class LLMChatModelEnum(TextChoices):
    # openai
    GPT_4O = "gpt-4o", "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini", "gpt-4o-mini"
    CHATGPT_4O_LATEST = "chatgpt-4o-latest", "chatgpt-4o-latest"
    O1 = "o1", "o1"
    O1_MINI = "o1-mini", "o1-mini"
    O3_MINI = "o3-mini", "o3-mini"
    # anthropic
    CLAUDE_3_7_SONNET_LATEST = "claude-3-7-sonnet-latest", "claude-3-7-sonnet-latest"
    CLAUDE_3_5_HAIKU_LATEST = "claude-3-5-haiku-latest", "claude-3-5-haiku-latest"
    CLAUDE_3_5_SONNET_LATEST = "claude-3-5-sonnet-latest", "claude-3-5-sonnet-latest"
    CLAUDE_3_OPUS_LATEST = "claude-3-opus-latest", "claude-3-opus-latest"
    # upstage
    UPSTAGE_SOLAR_PRO = "solar-pro", "solar-pro"
    UPSTAGE_SOLAR_MINI = "solar-mini", "solar-mini"
    # google
    GEMINI_2_0_FLASH = "gemini-2.0-flash", "gemini-2.0-flash"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite", "gemini-2.0-flash-lite"
    GEMINI_1_5_FLASH = "gemini-1.5-flash", "gemini-1.5-flash"
    GEMINI_1_5_FLASH_8B = "gemini-1.5-flash-8b", "gemini-1.5-flash-8b"
    GEMINI_1_5_PRO = "gemini-1.5-pro", "gemini-1.5-pro"
    # ollama
    LLAMA_3_3 = "llama3.3", "llama3.3"
    LLAMA_3_3_70B = "llama3.3:70b", "llama3.3:70b"
    LLAMA_3_2 = "llama3.2", "llama3.2"
    LLAMA_3_2_1B = "llama3.2:1b", "llama3.2:1b"
    LLAMA_3_2_3B = "llama3.2:3b", "llama3.2:3b"
    LLAMA_3_1 = "llama3.1", "llama3.1"
    LLAMA_3_1_8B = "llama3.1:8B", "llama3.1:8B"
    LLAMA_3_1_70B = "llama3.1:70B", "llama3.1:70B"
    LLAMA_3_1_405B = "llama3.1:405B", "llama3.1:405B"
    MISTRAL = "mistral", "mistral"
    MISTRAL_7B = "mistral:7b", "mistral:7b"
    QWEN2 = "qwen2", "qwen2"
    QWEN2_0_5B = "qwen2:0.5b", "qwen2:0.5b"
    QWEN2_1_5B = "qwen2:1.5b", "qwen2:1.5b"
    QWEN2_7B = "qwen2:7b", "qwen2:7b"
    QWEN2_72B = "qwen2:72b", "qwen2:72b"
    GEMMA3 = "gemma3", "gemma3"
    GEMMA3_1B = "gemma3:1b", "gemma3:1b"
    GEMMA3_4B = "gemma3:4b", "gemma3:4b"
    GEMMA3_12B = "gemma3:12b", "gemma3:12b"
    GEMMA3_27B = "gemma3:27b", "gemma3:27b"

    @classmethod
    def validate_model(cls, llm_vendor: LLMVendorType, chat_model: LLMChatModelType) -> None:
        """
        지정된 vendor에 해당 model이 존재하는지 검사합니다.

        Args:
            llm_vendor: 검사할 벤더 타입 ('openai', 'anthropic', 'google', 'ollama', 'upstage' 등)
            chat_model: 검사할 모델 이름

        Raises:
            ValidationError
        """

        if llm_vendor == LLMVendorEnum.OPENAI.value:
            if chat_model not in OpenAIChatModelEnum:
                raise ValidationError(f"{chat_model} : Invalid OpenAI Model")
        elif llm_vendor == LLMVendorEnum.ANTHROPIC.value:
            if chat_model not in AnthropicChatModelEnum:
                raise ValidationError(f"{chat_model} : Invalid Anthropic Model")
        elif llm_vendor == LLMVendorEnum.GOOGLE.value:
            if chat_model not in GoogleChatModelEnum:
                raise ValidationError(f"{chat_model} : Invalid Google Model")
        elif llm_vendor == LLMVendorEnum.OLLAMA.value:
            if chat_model not in OllamaChatModelEnum:
                raise ValidationError(f"{chat_model} : Invalid OLLAMA Model")
        elif llm_vendor == LLMVendorEnum.UPSTAGE.value:
            if chat_model not in UpstageChatModelEnum:
                raise ValidationError(f"{chat_model} : Invalid UPSTAGE Model")
        else:
            raise ValueError(f"Unknown llm vendor: {llm_vendor}")


assert enum_to_flatten_set(LLMVendorEnum) == type_to_flatten_set(
    LLMVendorType
), "Values in LLMVendorEnum and LLMVendorType do not match."
assert enum_to_flatten_set(LanguageEnum) == type_to_flatten_set(
    LanguageType
), "Values in LanguageEnum and LanguageType do not match."

assert enum_to_flatten_set(OpenAIChatModelEnum).issubset(
    type_to_flatten_set(OpenAIChatModelType)
), "OpenAIChatModelEnum is not a subset of OpenAIChatModelType."
assert enum_to_flatten_set(UpstageChatModelEnum) == type_to_flatten_set(
    UpstageChatModelType
), "Values in UpstageChatModelEnum and UpstageChatModelType do not match."
assert enum_to_flatten_set(AnthropicChatModelEnum).issubset(
    type_to_flatten_set(AnthropicChatModelType)
), "AnthropicChatModelEnum is not a subset of AnthropicChatModelType."
assert enum_to_flatten_set(GoogleChatModelEnum) == type_to_flatten_set(
    GoogleChatModelType
), "Values in GoogleChatModelEnum and GoogleChatModelType do not match."
assert enum_to_flatten_set(OllamaChatModelEnum) == type_to_flatten_set(
    OllamaChatModelType
), "Values in OllamaChatModelEnum and OllamaChatModelType do not match."

assert enum_to_flatten_set(LLMChatModelEnum) == (
    enum_to_flatten_set(OpenAIChatModelEnum)
    | enum_to_flatten_set(AnthropicChatModelEnum)
    | enum_to_flatten_set(UpstageChatModelEnum)
    | enum_to_flatten_set(GoogleChatModelEnum)
    | enum_to_flatten_set(OllamaChatModelEnum)
), "LLMChatModelEnum does not match the union of all vendor-specific ChatModelEnums."
