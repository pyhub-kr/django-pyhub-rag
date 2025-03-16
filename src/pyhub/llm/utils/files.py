import logging
import mimetypes
import re
from base64 import b64decode, b64encode
from enum import Enum
from io import BytesIO
from typing import IO, Literal, Optional, Set, TypeVar, Union

from django.core.files import File
from django.core.files.base import ContentFile
from django.utils.datastructures import MultiValueDict
from PIL import Image as PILImage

logger = logging.getLogger(__name__)


T = TypeVar("T")


class FileType(Enum):
    """지원하는 파일 타입 정의"""

    IMAGE = "image"
    TEXT = "text"
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    MARKDOWN = "markdown"
    ANY = "any"  # 모든 타입 허용

    @classmethod
    def get_mimetypes(cls, file_type: "FileType") -> Set[str]:
        """파일 타입에 해당하는 MIME 타입 목록 반환"""
        mime_mappings = {
            cls.IMAGE: {"image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp"},
            cls.TEXT: {"text/plain"},
            cls.PDF: {"application/pdf"},
            cls.CSV: {"text/csv"},
            cls.JSON: {"application/json"},
            cls.MARKDOWN: {"text/markdown"},
            cls.ANY: {
                "image/jpeg",
                "image/png",
                "image/gif",
                "image/bmp",
                "image/webp",
                "text/plain",
                "application/pdf",
                "text/csv",
                "application/json",
                "text/markdown",
            },
        }
        return mime_mappings.get(file_type, set())


def encode_files(
    files: Optional[list[File]] = None,
    allowed_types: Union[FileType, list[FileType]] = FileType.IMAGE,
    convert_mode: Literal["base64", "url"] = "base64",
    image_max_size: int = 512,
    image_quality: int = 60,
    image_resampling: PILImage.Resampling = PILImage.Resampling.LANCZOS,
) -> list[str]:
    """파일을 인코딩하여 반환합니다.

    Args:
        files (Optional[List[File]]): 파일 목록
        allowed_types (Union[FileType, List[FileType]]): 허용할 파일 타입
        image_max_size (int): 이미지의 경우 최대 허용 픽셀 크기
        image_quality (int): 이미지의 경우 JPEG 품질 설정 (1-100)
        image_resampling (int): 이미지 리샘플링 방법
        convert_mode (str): 인코딩 모드 ("base64" 또는 "url")

    Returns:
        List[str]: 인코딩된 파일 목록

    Examples:
        >>> # 이미지만 처리
        >>> encode_files(files, allowed_types=FileType.IMAGE)
        >>> # 이미지와 PDF만 처리
        >>> encode_files(files, allowed_types=[FileType.IMAGE, FileType.PDF])
    """
    if not files:
        return []

    if isinstance(allowed_types, FileType):
        allowed_types = [allowed_types]

    allowed_mimetypes = set()
    for file_type in allowed_types:
        allowed_mimetypes.update(FileType.get_mimetypes(file_type))

    encoded_urls = []

    if convert_mode == "base64":
        for file in files:
            content_type = mimetypes.guess_type(file.name)[0]

            if not content_type:
                logger.warning(f"Unknown content type for file: {file.name}")
                continue

            if content_type not in allowed_mimetypes:
                logger.warning(
                    f"File type not allowed: {content_type} for {file.name}. "
                    f"Allowed types: {', '.join(allowed_mimetypes)}"
                )
                continue

            try:
                if content_type.startswith("image/"):
                    optimized_image, content_type = optimize_image(
                        file.file,
                        max_size=image_max_size,
                        quality=image_quality,
                        resampling=image_resampling,
                    )
                    prefix = f"data:{content_type};base64,"
                    b64_string = b64encode(optimized_image).decode("utf-8")
                    encoded_urls.append(f"{prefix}{b64_string}")
                else:
                    # 이미지가 아닌 파일은 직접 base64 인코딩
                    content = file.read()
                    if isinstance(content, str):
                        content = content.encode("utf-8")
                    prefix = f"data:{content_type};base64,"
                    b64_string = b64encode(content).decode("utf-8")
                    encoded_urls.append(f"{prefix}{b64_string}")
            except Exception as e:
                logger.error(f"Error processing file {file.name}: {str(e)}")
                continue

    elif convert_mode == "url":
        logger.info("URL 모드는 아직 구현되지 않았습니다.")
        pass
    else:
        logger.warning(f"Unsupported encoding mode: {convert_mode}. Using base64 instead.")
        return encode_files(files, allowed_types, image_max_size, image_quality, image_resampling, "base64")

    return encoded_urls


def optimize_image(
    image_file: IO,
    max_size: int = 1024,
    quality: int = 80,
    resampling: PILImage.Resampling = PILImage.Resampling.LANCZOS,
) -> tuple[bytes, str]:
    """이미지를 최적화하여 bytes로 반환합니다.

    Args:
        image_file: 이미지 파일 객체
        max_size (int): 최대 허용 픽셀 크기 (가로/세로 중 큰 쪽 기준)
        quality (int): JPEG 품질 설정 (1-100)
        resampling (int): 리샘플링 방법

    Returns:
        bytes: 최적화된 이미지의 바이트 데이터
    """
    # 이미지 열기
    img = PILImage.open(image_file)

    # RGBA to RGB (PNG -> JPEG 변환 시 필요)
    if img.mode == "RGBA":
        bg = PILImage.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg

    # 이미지 크기 조정
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        width, height = (int(dim * ratio) for dim in img.size)
        img = img.resize((width, height), resampling)

    # 최적화된 이미지를 바이트로 변환
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)

    return buffer.getvalue(), "image/jpeg"


def extract_base64_files(request_dict: dict, base64_field_name_postfix: str = "__base64") -> MultiValueDict:
    """base64로 인코딩된 파일 데이터를 디코딩하여 Django의 MultiValueDict 형태로 반환합니다.

    request_dict에서 field_name_postfix로 끝나는 필드를 찾아 base64로 인코딩된 파일 데이터를 디코딩합니다.
    현재는 이미지 파일만 처리합니다.

    Args:
        request_dict (Dict): 요청 데이터를 담고 있는 딕셔너리.
        base64_field_name_postfix (str): base64로 인코딩된 파일 필드 이름 접미사

    Returns:
        MultiValueDict: 디코딩된 파일들을 담고 있는 Django의 MultiValueDict 객체.
            키는 원본 필드 이름(접미사 제외)이고, 값은 ContentFile 객체들의 리스트.

    Examples:
        >>> files = decode_base64_files({
        ...     "image__base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgA..."
        ... })
        >>> files.getlist("image")[0]  # ContentFile 객체 반환
    """
    files = MultiValueDict()
    for field_name in request_dict.keys():
        if field_name.endswith(base64_field_name_postfix):
            file_field_name = re.sub(rf"{base64_field_name_postfix}$", "", field_name)
            file_list: list[File] = []
            for base64_str in request_dict[field_name].split("||"):
                if base64_str.startswith("data:image/"):
                    header, data = base64_str.split(",", 1)
                    matched = re.search(r"data:([^;]+);base64", header)
                    if matched and "image/" in matched.group(1):
                        extension: str = matched.group(1).split("/", 1)[-1]
                        file_name = f"{file_field_name}.{extension}"
                        file_list.append(ContentFile(b64decode(data), name=file_name))

            if file_list:
                files.setlist(file_field_name, file_list)
    return files


class Mimetypes(Enum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    BMP = "image/bmp"
    WEBP = "image/webp"


IMAGE_SIGNATURES = {
    "jpeg": [
        (0, bytes([0xFF, 0xD8, 0xFF]), Mimetypes.JPEG),
        (0, bytes([0xFF, 0xD8, 0xFF, 0xE0]), Mimetypes.JPEG),
        (0, bytes([0xFF, 0xD8, 0xFF, 0xE1]), Mimetypes.JPEG),
    ],
    "png": [(0, bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]), Mimetypes.PNG)],
    "gif": [(0, b"GIF87a", Mimetypes.GIF), (0, b"GIF89a", Mimetypes.GIF)],
    "bmp": [(0, bytes([0x42, 0x4D]), Mimetypes.BMP)],
    "webp": [(8, b"WEBP", Mimetypes.WEBP)],
}


def get_image_mimetype(header: bytes) -> Optional[Mimetypes]:
    for format_name, format_sigs in IMAGE_SIGNATURES.items():
        for offset, signature, mimetype in format_sigs:
            if header[offset : offset + len(signature)] == signature:
                return mimetype
    return None
