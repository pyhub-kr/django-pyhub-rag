import json

import numpy as np
import pytest
from django.core.exceptions import ValidationError

from pyhub.rag.fields.sqlite import SQLiteVectorField


@pytest.mark.it("SQLiteVectorField는 벡터 데이터를 JSON 문자열로 저장하고 numpy 배열로 변환해야 합니다.")
@pytest.mark.parametrize(
    "input_value,expected_type,expected_dimensions",
    [
        ([0.1] * 1536, np.ndarray, 1536),
        (np.array([0.1] * 1536), np.ndarray, 1536),
        (json.dumps([0.1] * 1536), np.ndarray, 1536),
    ],
)
def test_vector_field_conversion(input_value, expected_type, expected_dimensions):
    field = SQLiteVectorField(dimensions=expected_dimensions)

    # to_python 메서드 테스트
    python_value = field.to_python(input_value)
    assert isinstance(python_value, expected_type)
    assert len(python_value) == expected_dimensions

    # get_prep_value 메서드 테스트
    db_value = field.get_prep_value(python_value)
    assert isinstance(db_value, str)
    assert len(json.loads(db_value)) == expected_dimensions


@pytest.mark.it("SQLiteVectorField는 차원 검증을 올바르게 수행해야 합니다.")
def test_dimension_validation():
    field = SQLiteVectorField(dimensions=1536)

    # 올바른 차원의 데이터
    valid_data = [0.1] * 1536
    assert field.to_python(valid_data) is not None

    # 잘못된 차원의 데이터
    invalid_data = [0.1] * 1000
    with pytest.raises(ValidationError) as exc_info:
        field.to_python(invalid_data)
    assert "dimensions" in str(exc_info.value)


@pytest.mark.it("SQLiteVectorField는 잘못된 입력값을 적절히 처리해야 합니다.")
@pytest.mark.parametrize(
    "invalid_input",
    [
        "not a json",
        "{}",  # 유효하지 않은 JSON (리스트가 아님)
        42,  # 숫자
        {"key": "value"},  # 딕셔너리
    ],
)
def test_invalid_input_handling(invalid_input):
    field = SQLiteVectorField(dimensions=1536)

    with pytest.raises(ValidationError):
        field.to_python(invalid_input)


@pytest.mark.it("SQLiteVectorField는 None 값을 허용해야 합니다.")
def test_null_handling():
    field = SQLiteVectorField(dimensions=1536, null=True)

    assert field.to_python(None) is None
    assert field.get_prep_value(None) is None
