from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.fields.files import FieldFile
from django.forms import FileInput, TextInput


class PDFFileField(models.FileField):
    validators = [FileExtensionValidator(allowed_extensions=["pdf"])]

    def validate(self, value: FieldFile, model_instance):
        super().validate(value, model_instance)

        try:
            # 헤더만 읽되, 헤더에 잡다한 바이트가 있을 수 있으므로 최대 1024바이트까지 검사
            head = value.read(1024)
            if b"%PDF-" not in head:
                raise ValidationError("The uploaded file is not a valid PDF document.")
        finally:
            value.seek(0)

    def formfield(self, **kwargs):
        kwargs["widget"] = FileInput(attrs={"accept": "application/pdf"})
        return super().formfield(**kwargs)


class PageNumbersField(models.CharField):
    description = "Comma-separated page numbers with min/max validation"

    def __init__(self, min_page=1, max_page=None, *args, **kwargs):
        if max_page is not None and max_page < min_page:
            raise ValueError("max_page는 min_page보다 크거나 같아야 합니다.")

        self.min_page = min_page
        self.max_page = max_page
        kwargs.setdefault("max_length", 255)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        """데이터베이스에서 값을 가져올 때 자동으로 리스트로 변환"""
        if value is None:
            return []
        return sorted(set(int(x) for x in value.split(",") if x.strip()))

    def get_prep_value(self, value):
        """Python 값을 데이터베이스에 저장하기 전에 문자열로 변환"""
        if not value:  # None이나 빈 리스트인 경우
            return ""
        # 리스트를 정렬하고 중복을 제거한 후 문자열로 변환
        if isinstance(value, str):
            value = [int(x) for x in value.split(",") if x.strip()]
        numbers = sorted(set(value))
        return ",".join(str(num) for num in numbers)

    def to_python(self, value):
        if not value:
            return []
        # 문자열인 경우 리스트로 변환
        if isinstance(value, str):
            numbers = [int(x) for x in value.split(",") if x.strip()]
        else:
            numbers = value
        return sorted(set(int(x) for x in numbers))

    def validate(self, value, model_instance):
        super().validate(value, model_instance)

        try:
            numbers = self.to_python(value)
        except ValueError as e:
            raise ValidationError(f"유효하지 않은 페이지 번호 형식입니다: {str(e)}")

        for num in numbers:
            if num < self.min_page:
                raise ValidationError(f"페이지 번호는 {self.min_page} 이상이어야 합니다.")
            if self.max_page and num > self.max_page:
                raise ValidationError(f"페이지 번호는 {self.max_page} 이하여야 합니다.")

    def formfield(self, **kwargs):
        defaults = {"widget": TextInput(attrs={"placeholder": "예: 1,2,4,5"})}
        defaults.update(kwargs)
        return super().formfield(**defaults)


__all__ = ["PDFFileField", "PageNumbersField"]
