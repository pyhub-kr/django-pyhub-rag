import base64
import hashlib
import logging
import mimetypes
import re
from typing import Optional, Tuple

from django.core.files import File
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


def base64_to_file(base64_data: str, filename: Optional[str] = None) -> File:
    """
    Base64 데이터를 디코딩하여 Django File 객체로 변환합니다.
    파일 헤더를 분석하여 MIME 타입과 확장자를 유추하고, MD5 해시를 사용하여 파일명을 생성합니다.

    Args:
        base64_data (str): Base64로 인코딩된 파일 데이터
        filename (str, optional): 생성될 파일명. 미지정시에 md5 해시값 생성

    Returns:
        File: Django File 객체

    Raises:
        ValueError: Base64 디코딩에 실패한 경우 발생합니다.
    """
    try:
        # Base64 데이터에서 헤더 제거 (있는 경우)
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]

        file_bytes: bytes = base64.b64decode(base64_data)
        mimetype, extension = get_mimetype_and_extension_from_header(file_bytes)

        if not filename:
            filename = hashlib.md5(file_bytes).hexdigest()

        filename = f"{filename}{extension}"

        return ContentFile(file_bytes, name=filename)

    except Exception as e:
        raise ValueError(f"Base64 데이터를 파일로 변환하는 중 오류 발생: {e}")


def get_mimetype_and_extension_from_header(file_bytes: bytes) -> Tuple[str, str]:
    """
    파일 헤더(매직 바이트)를 분석하여 MIME 타입과 파일 확장자를 유추합니다.

    Args:
        file_bytes (bytes): 파일 바이트 데이터

    Returns:
        Tuple[str, str]: (MIME 타입, 파일 확장자) 튜플 (확장자는 점 포함, 예: '.pdf')
    """
    # 일반적인 파일 형식의 매직 바이트와 해당 MIME 타입 매핑
    magic_bytes_to_mime = {
        b"%PDF": "application/pdf",
        b"\x89PNG": "image/png",
        b"\xff\xd8\xff": "image/jpeg",
        b"GIF8": "image/gif",
        b"PK\x03\x04": "application/zip",  # 기본 ZIP
        b"\x50\x4b\x03\x04\x14\x00\x06\x00": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
        b"\x50\x4b\x03\x04\x14\x00\x08\x00": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
        b"JFIF": "image/jpeg",
        b"RIFF": "audio/wav",
        b"\x1a\x45\xdf\xa3": "video/webm",
        b"\x00\x00\x00\x14ftypisom": "video/mp4",
    }

    # 파일 헤더 확인
    mimetype = None
    for magic, mime in magic_bytes_to_mime.items():
        if file_bytes.startswith(magic):
            mimetype = mime
            break

    # 텍스트 파일 확인 (UTF-8, ASCII 등)
    if mimetype is None:
        try:
            content_start = file_bytes[:20].decode("utf-8")
            if re.match(r"^<!DOCTYPE html|^<html", content_start, re.IGNORECASE):
                mimetype = "text/html"
            elif re.match(r"^{|\[", content_start):
                mimetype = "application/json"
            elif re.match(r"^#!|^import|^def|^class|^from", content_start):
                mimetype = "text/x-python"
        except UnicodeDecodeError:
            pass

    # 기본 MIME 타입
    if mimetype is None:
        mimetype = "application/octet-stream"

    # MIME 타입에서 확장자 추출
    extension = get_extension_from_mimetype(mimetype)

    return mimetype, extension


def get_extension_from_mimetype(mimetype: str) -> str:
    """
    MIME 타입으로부터 파일 확장자를 추출합니다.

    Args:
        mimetype (str): MIME 타입 문자열

    Returns:
        str: 파일 확장자 (점 포함, 예: '.pdf')
    """
    # mimetypes 모듈을 사용하여 확장자 가져오기
    extension = mimetypes.guess_extension(mimetype)

    # 특정 MIME 타입에 대한 기본 확장자 재정의
    mime_to_ext_override = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "text/html": ".html",
        "application/json": ".json",
        "text/x-python": ".py",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    }

    if mimetype in mime_to_ext_override:
        return mime_to_ext_override[mimetype]

    # mimetypes 모듈이 확장자를 찾지 못한 경우 기본값 반환
    if extension is None:
        return ".bin"

    return extension
