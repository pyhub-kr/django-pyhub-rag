import base64
import hashlib
import logging
import mimetypes
import re
from pathlib import Path
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


def manage_cache_directory(cache_dir: Path, max_size_mb: int = 512) -> None:
    """
    캐시 디렉토리의 크기를 관리합니다. 최대 용량을 초과하면 오래된 파일부터 삭제합니다.

    Args:
        cache_dir: 캐시 디렉토리 경로
        max_size_mb: 최대 허용 크기 (MB 단위)
    """

    if not cache_dir.exists():
        return

    # 최대 크기를 바이트 단위로 변환
    max_size_bytes = max_size_mb * 1024 * 1024

    # 현재 캐시 디렉토리 크기 계산
    total_size = sum(f.stat().st_size for f in cache_dir.glob("**/*") if f.is_file())
    logger.debug("현재 캐시 크기: %.2fMB / 최대 %dMB", total_size / (1024 * 1024), max_size_mb)

    # 최대 크기를 초과하지 않으면 아무 작업도 하지 않음
    if total_size <= max_size_bytes:
        return
    else:
        # 파일 목록을 수정 시간 기준으로 정렬 (오래된 것부터)
        files = [(f, f.stat().st_mtime) for f in cache_dir.glob("**/*") if f.is_file()]
        files.sort(key=lambda x: x[1])  # 수정 시간 기준 정렬
        logger.info("캐시 정리 시작: %d개 파일 중 오래된 파일부터 삭제합니다.", len(files))

        # 필요한 만큼 오래된 파일부터 삭제
        deleted_count = 0
        deleted_size = 0

        for file_path, __ in files:
            if total_size <= max_size_bytes:
                break

            file_size = file_path.stat().st_size
            try:
                file_path.unlink()
                total_size -= file_size
                deleted_size += file_size
                deleted_count += 1
                logger.debug("캐시 파일 삭제: %s (%.1fKB)", file_path.name, file_size / 1024)
            except (PermissionError, OSError) as e:
                # 파일 삭제 실패 시 계속 진행
                logger.warning("캐시 파일 삭제 실패: %s - %s", file_path, str(e))
                continue

        if deleted_count > 0:
            logger.info("캐시 정리 완료: %d개 파일 삭제, %.2fMB 확보됨", deleted_count, deleted_size / (1024 * 1024))
