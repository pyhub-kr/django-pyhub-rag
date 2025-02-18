from pgvector.django import HalfVectorField

from pyhub.rag.fields import VectorField
from pyhub.rag.settings import rag_settings


def test_field_initialization():
    field = VectorField()
    assert field.dimensions == rag_settings.RAG_EMBEDDING_DIMENSIONS
    assert field.embedding_model == rag_settings.RAG_EMBEDDING_MODEL


def test_field_with_custom_dimensions():
    field = VectorField(dimensions=512)
    assert field.dimensions == 512


def test_field_deconstruct():
    field = VectorField(dimensions=512, openai_api_key="test-key", embedding_model="test-model")
    name, path, args, kwargs = field.deconstruct()

    assert kwargs["dimensions"] == 512
    assert kwargs["openai_api_key"] == "test-key"
    assert kwargs["embedding_model"] == "test-model"


def test_half_vector_field_behavior():
    # OpenAI의 기본 임베딩 차원(1536)의 2배로 설정
    field = VectorField(dimensions=1536 * 2)

    # HalfVector 모드로 동작하는지 확인
    assert field.vector_field_class == HalfVectorField
    assert field.dimensions == 1536 * 2
