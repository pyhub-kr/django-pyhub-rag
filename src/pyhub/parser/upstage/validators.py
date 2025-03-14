import logging
import os
from typing import Callable, Dict, List

from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import FileExtensionValidator

from pyhub.parser.validators import (
    FileSizeValidator,
    ImageConstraintsValidator,
    PDFValidator,
)

from .settings import (
    MAX_FILE_SIZE_MB,
    MAX_PIXELS_PER_PAGE,
    SUPPORTED_FILE_EXTENSIONS,
)

logger = logging.getLogger(__name__)


# Validator registry
COMMON_VALIDATORS: List[Callable[[File], None]] = [
    FileExtensionValidator(SUPPORTED_FILE_EXTENSIONS),
    FileSizeValidator(MAX_FILE_SIZE_MB),
]


FORMAT_VALIDATORS: Dict[str, List[Callable[[File], None]]] = {
    ".pdf": [PDFValidator()],
    (".jpeg", ".jpg", ".png", ".bmp", ".tiff", ".tif", ".heic"): [ImageConstraintsValidator(MAX_PIXELS_PER_PAGE)],
}


def validate_upstage_document(file: File) -> None:
    """
    Upstage Document Parse API 제약 조건에 대해 파일을 검증합니다.
    모든 적용 가능한 검증기를 실행하여 모든 검증 오류를 수집합니다.

    Args:
        file: 검증할 파일

    Raises:
        ValidationError: 파일이 검증 확인에 실패하면 모든 오류 메시지와 함께 발생
    """
    errors: list[ValidationError] = []

    # Run common validators
    for validator in COMMON_VALIDATORS:
        _run_validator(validator, file, errors)

    # Run format-specific validators
    ext = os.path.splitext(file.name.lower())[-1]

    for formats, validators in FORMAT_VALIDATORS.items():
        if (formats == ext) or (isinstance(formats, (tuple, list)) and ext in formats):
            for validator in validators:
                _run_validator(validator, file, errors)

    # Raise all collected errors
    if errors:
        raise ValidationError(errors)


def _get_validator_name(validator: Callable) -> str:
    """
    검증기 함수나 클래스의 이름을 추출합니다.

    Args:
        validator: 검증기 함수나 클래스

    Returns:
        str: 검증기의 이름
    """
    return (
        validator.__class__.__name__ if hasattr(validator, "__class__") and callable(validator) else validator.__name__
    )


def _run_validator(validator: Callable[[File], None], file: File, errors: list[ValidationError]) -> bool:
    """
    단일 검증기를 실행하고 로깅 및 오류 수집을 처리합니다.

    Args:
        validator: 실행할 검증기
        file: 검증할 파일
        errors: 검증 오류를 수집할 리스트

    Returns:
        bool: 검증이 통과되면 True, 그렇지 않으면 False
    """
    validator_name = _get_validator_name(validator)
    try:
        validator(file)
        logger.debug("File '%s' passed validation: %s", file.name, validator_name)
        return True
    except ValidationError as e:
        logger.debug("File '%s' failed validation: %s", file.name, str(e))
        errors.append(e)
        return False
