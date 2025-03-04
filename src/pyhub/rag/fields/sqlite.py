import sqlite3
from typing import Optional

import numpy as np
from django import forms
from django.apps import apps
from django.core import checks
from django.core.exceptions import ValidationError

from pyhub.rag.fields.base import BaseVectorField
from pyhub.rag.json import JSONDecodeError, json_dumps, json_loads


class SQLiteVectorField(BaseVectorField):
    """
    A Django model field for storing vector embeddings in SQLite using the sqlite-vec extension.
    The field stores the vector as a JSON array string and returns a numpy array internally.
    """

    description = "SQLite vector"
    empty_strings_allowed = False

    def __init__(self, dimensions: Optional[int] = None, **kwargs):
        """
        :param dimensions: Expected number of vector components. If provided, the input vector
                           length is validated to match.
        """
        super().__init__(dimensions=dimensions, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()

        # dimensions는 명시적으로 포함시키지만, 아래 커스텀 옵션은 마이그레이션 대상에서 제거합니다.
        kwargs.pop("embedding_max_tokens_limit", None)
        kwargs.pop("embedding_model", None)
        kwargs.pop("openai_api_key", None)
        kwargs.pop("openai_base_url", None)
        kwargs.pop("google_api_key", None)

        if self.dimensions is not None:
            kwargs["dimensions"] = self.dimensions

        return name, path, args, kwargs

    def db_type(self, connection):
        """
        Returns the database column data type.
        For sqlite-vec, if dimensions is provided it will be "float[N]".
        If dimensions is not provided, it defaults to "float[]" (SQLite is flexible about types).
        """
        if self.dimensions is None:
            return "float[]"
        return "float[%d]" % self.dimensions

    def from_db_value(self, value, expression, connection):
        """
        Converts the JSON string from the database back to a numpy array.
        """
        if value is None:
            return value
        return self.to_python(value)

    def to_python(self, value):
        """
        Converts the input value into a numpy array of type float32.
        Accepts None, numpy array, list, or JSON string. Performs dimension validation if needed.
        """
        if value is None or isinstance(value, np.ndarray):
            return value

        # If the value is a bytes object, decode it to a string
        if isinstance(value, bytes):
            return np.frombuffer(value, dtype=np.float32)

        # If the value is already a list, convert it to np.array
        if isinstance(value, list):
            arr = np.array(value, dtype=np.float32)
            if self.dimensions is not None and arr.size != self.dimensions:
                raise ValidationError(f"Expected vector with {self.dimensions} dimensions, got {arr.size}.")
            return arr

        # If the value is a string, try to parse it as JSON.
        if isinstance(value, str):
            try:
                parsed = json_loads(value)
            except JSONDecodeError:
                raise ValidationError("Invalid JSON format for vector field.")
            if not isinstance(parsed, list):
                raise ValidationError("JSON value for vector field must be a list.")
            arr = np.array(parsed, dtype=np.float32)
            if self.dimensions is not None and arr.size != self.dimensions:
                raise ValidationError(f"Expected vector with {self.dimensions} dimensions, got {arr.size}.")
            return arr

        # Attempt conversion from any other type
        try:
            arr = np.array(value, dtype=np.float32)
        except Exception:
            raise ValidationError("Invalid type for vector field; expected list, numpy array, or JSON string.")
        if self.dimensions is not None and arr.size != self.dimensions:
            raise ValidationError(f"Expected vector with {self.dimensions} dimensions, got {arr.size}.")
        return arr

    def get_prep_value(self, value):
        """
        Prepares the value for saving into the database.
        Converts numpy arrays and lists to a JSON string.
        """
        if value is None:
            return value
        if isinstance(value, np.ndarray):
            if self.dimensions is not None and value.size != self.dimensions:
                raise ValidationError(f"Expected vector with {self.dimensions} dimensions, got {value.size}.")
            value = value.tolist()
        elif isinstance(value, list):
            if self.dimensions is not None and len(value) != self.dimensions:
                raise ValidationError(f"Expected vector with {self.dimensions} dimensions, got {len(value)}.")
        return json_dumps(value)

    def value_to_string(self, obj):
        """
        Returns a string representation of the field value.
        """
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    def formfield(self, **kwargs):
        """
        Specifies the default form widget and field for this model field.
        """
        defaults = {"form_class": SQLiteVectorFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def check(self, **kwargs):
        errors = super().check(**kwargs)

        def add_error(msg: str, hint: str = None):
            errors.append(checks.Error(msg, hint=hint, obj=self))

        if self.embedding_model == "text-embedding-3-small":
            if self.dimensions > 2000:
                add_error(
                    f"{self.dimensions} 차원은 {self.embedding_model} 모델로 임베딩할 수 없습니다.",
                    hint="2000차원 이상은 text-embedding-3-large 모델로 변경해주세요.",
                )

        db = sqlite3.connect(":memory:")
        if hasattr(db, "enable_load_extension") is False:
            add_error(
                "현재 파이썬 사용 중이신 파이썬 인터프리터의 sqlite3 모듈은 확장을 지원하지 않습니다.",
                hint=(
                    "sqlite3 확장이 지원되는 파이썬 인터프리터를 설치하신 후에 활용해주세요.\n"
                    "(참고: https://ai.pyhub.kr/setup/vector-stores/sqlite-vec, 문의: help@pyhub.kr)"
                ),
            )

        if not apps.is_installed("pyhub.rag"):
            add_error(
                "'pyhub.rag' app is not installed.",
                hint="Add 'pyhub.rag' to INSTALLED_APPS in your Django settings.",
            )

        return errors


class SQLiteVectorWidget(forms.TextInput):
    """
    A widget that displays the vector field as a JSON string.
    """

    def format_value(self, value):
        if isinstance(value, np.ndarray):
            value = value.tolist()
        # If the value is a list, format it as a JSON string;
        # otherwise, pass the value as-is.
        if isinstance(value, list):
            return json_dumps(value)
        return value


class SQLiteVectorFormField(forms.CharField):
    """
    A Django form field for the SQLiteVectorField.
    It converts input text (JSON list) to a Python list.
    """

    widget = SQLiteVectorWidget

    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return None
        if isinstance(value, list) or isinstance(value, np.ndarray):
            return value
        try:
            parsed = json_loads(value)
        except JSONDecodeError:
            raise ValidationError("Enter a valid JSON list for the vector field.")
        if not isinstance(parsed, list):
            raise ValidationError("Enter a valid JSON list for the vector field.")
        return parsed

    def has_changed(self, initial, data):
        """
        Compares the initial value with the submitted data.
        """
        if isinstance(initial, np.ndarray):
            initial = initial.tolist()
        if isinstance(data, list):
            return super().has_changed(json_dumps(initial), json_dumps(data))
        return super().has_changed(initial, data)
