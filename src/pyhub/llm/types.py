from collections import namedtuple
from dataclasses import dataclass
from typing import Literal, TypeAlias, Union

from anthropic.types import ModelParam as AnthropicChatModel
from openai.types import ChatModel as OpenAIChatModel
from pydantic import BaseModel
from typing_extensions import Optional

OpenAIEmbeddingModel: TypeAlias = Literal[
    "text-embedding-ada-002",  # 1536 차원
    "text-embedding-3-small",  # 1536 차원
    "text-embedding-3-large",  # 3072 차원
]

# https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings?hl=ko
GoogleEmbeddingModel: TypeAlias = Literal["text-embedding-004"]  # 768 차원

LLMEmbeddingModel = Union[OpenAIEmbeddingModel, GoogleEmbeddingModel]


# https://ai.google.dev/gemini-api/docs/models/gemini?hl=ko
GoogleChatModel: TypeAlias = Union[
    Literal[
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ],
]


LLMChatModel: TypeAlias = Union[OpenAIChatModel, AnthropicChatModel, GoogleChatModel]


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "function"]
    content: str


Usage = namedtuple("Usage", ["input", "output"])


@dataclass
class Reply:
    text: str
    usage: Optional[Usage] = None

    def __str__(self) -> str:
        return self.text
