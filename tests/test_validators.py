import pytest
from django.core.exceptions import ValidationError

from pyhub.rag.validators import MaxTokenValidator


def test_max_token_validator():
    validator = MaxTokenValidator(model_name="text-embedding-3-small")

    # Valid text
    validator("Short text")  # Should not raise

    # Invalid text (too long)
    long_text = "test " * 9000
    with pytest.raises(ValidationError):
        validator(long_text)


def test_invalid_model_validator():
    with pytest.raises(ValidationError):
        MaxTokenValidator(model_name="invalid-model")("test")
