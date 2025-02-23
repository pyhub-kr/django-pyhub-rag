import pytest
from pgvector.django import HalfVectorField, VectorField

from pyhub.rag.fields.postgres import PGVectorField


@pytest.mark.it("PGVectorField 타입 필드는 지정한 차원에 맞게 필드 타입을 지정해야만 합니다.")
@pytest.mark.parametrize(
    "dimensions,expected_field_type",
    [
        (1536, VectorField),
        (3072, HalfVectorField),
    ],
)
def test_half_vector_field_behavior(dimensions, expected_field_type):
    field = PGVectorField(dimensions=dimensions)

    assert isinstance(field.vector_field, expected_field_type)
    assert field.dimensions == dimensions
