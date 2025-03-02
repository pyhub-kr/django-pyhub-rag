import pytest

from pyhub.rag.fields import BaseVectorField
from pyhub.rag.settings import rag_settings


@pytest.mark.it("BaseVectorField가 rag_settings의 기본 설정으로 초기화되는지 테스트합니다.")
def test_field_initialization():
    field = BaseVectorField()
    assert field.dimensions == rag_settings.embedding_dimensions
    assert field.embedding_model == rag_settings.embedding_model


@pytest.mark.it("사용자 정의 차원이 기본값을 덮어쓰는지 테스트합니다.")
def test_field_with_custom_dimensions():
    field = BaseVectorField(dimensions=512)
    assert field.dimensions == 512


@pytest.mark.it("deconstruct 메서드가 올바른 설정 값을 kwargs에 반환하는지 테스트합니다.")
def test_field_deconstruct():
    field = BaseVectorField(dimensions=512, openai_api_key="test-key", embedding_model="test-model")
    name, path, args, kwargs = field.deconstruct()

    assert kwargs["dimensions"] == 512
    assert kwargs["openai_api_key"] == "test-key"
    assert kwargs["embedding_model"] == "test-model"
