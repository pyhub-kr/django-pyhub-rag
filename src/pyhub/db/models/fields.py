from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.fields.files import FieldFile
from django.forms import FileInput


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


__all__ = ["PDFFileField"]