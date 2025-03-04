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
