import pytest
from django.core.exceptions import ValidationError

from pyhub.rag.validators import MaxTokenValidator


@pytest.mark.it("텍스트가 유효한 경우는 통과하고, 토큰 수 초과 시 ValidationError가 발생하는지 테스트합니다.")
def test_max_token_validator():
    validator = MaxTokenValidator(model_name="text-embedding-3-small")

    # Valid text
    validator("Short text")  # Should not raise

    # Invalid text (too long)
    long_text = "test " * 9000
    with pytest.raises(ValidationError):
        validator(long_text)


@pytest.mark.it("유효하지 않은 모델 이름이 주어졌을 때, ValidationError가 발생하는지 테스트합니다.")
def test_invalid_model_validator():
    with pytest.raises(ValidationError):
        MaxTokenValidator(model_name="invalid-model")("test")
