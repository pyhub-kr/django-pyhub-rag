from django.core.exceptions import ValidationError
from django.core.files import File
from django.utils.deconstruct import deconstructible
from PIL import Image as PILImage
from PyPDF2 import PdfReader
from PyPDF2.errors import PyPdfError


@deconstructible
class FileSizeValidator:
    """
    파일 크기 제약 조건에 대한 검증기 클래스입니다.
    """

    def __init__(self, max_size_mb: float):
        """
        최대 크기 제한으로 파일 크기 검증기를 초기화합니다.

        Args:
            max_size_mb: 메가바이트 단위의 최대 파일 크기
        """
        self.max_size_mb = max_size_mb

    def __call__(self, file: File) -> None:
        """
        파일 크기가 제한 내에 있는지 검증합니다.

        Args:
            file: 검증할 파일

        Raises:
            ValidationError: 파일 크기가 최대 제한을 초과하는 경우 발생
        """
        file_size_mb = file.size / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            raise ValidationError(
                f"File size exceeds the maximum limit of {self.max_size_mb}MB (current size: {file_size_mb:.2f}MB)"
            )


@deconstructible
class PDFValidator:
    def __call__(self, file: File) -> None:
        try:
            PdfReader(file)
            file.seek(0)
        except PyPdfError as e:
            raise ValidationError(f"Failed to validate PDF: {str(e)}")


@deconstructible
class ImageConstraintsValidator:
    """
    이미지 특정 제약 조건(픽셀 수)에 대한 검증기 클래스입니다.
    """

    def __init__(self, max_pixels_per_page: int):
        """
        최대 픽셀 제한으로 이미지 제약 조건 검증기를 초기화합니다.

        Args:
            max_pixels_per_page: 이미지에서 허용되는 최대 픽셀 수
        """
        self.max_pixels_per_page = max_pixels_per_page

    def __call__(self, file: File) -> None:
        """
        이미지 특정 제약 조건(픽셀 수)을 검증합니다.

        Args:
            file: 검증할 이미지 파일

        Raises:
            ValidationError: 이미지가 픽셀 제한을 초과하는 경우 발생
        """
        try:
            img = PILImage.open(file)
            width, height = img.size
            pixel_count = width * height
            if pixel_count > self.max_pixels_per_page:
                raise ValidationError(f"Image exceeds the maximum pixel limit of {self.max_pixels_per_page} pixels")
            file.seek(0)
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Failed to validate image: {str(e)}")
