import logging
from hashlib import md5
from io import IOBase
from pathlib import Path
from typing import Union

from django.core.cache import caches
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.files import File

logger = logging.getLogger(__name__)


def cache_clear(alias: str = "default") -> None:
    caches[alias].clear()


async def cache_clear_async(alias: str = "default") -> None:
    await caches[alias].aclear()


def cache_make_key(
    args: list[
        Union[
            int,
            float,
            str,
            dict[str, Union[str, int, File, IOBase]],
        ]
    ],
) -> str:
    """
    주어진 인자들을 기반으로 캐시 키를 생성합니다.

    Args:
        args (list): 캐시 키 생성에 사용할 인자 리스트

    Returns:
        Path: 캐시 파일 경로
    """
    hasher = md5()

    for arg in args:
        if isinstance(arg, dict):
            for key, value in sorted(arg.items()):
                if isinstance(value, (File, IOBase)):
                    current_pos = value.tell()
                    value.seek(0)

                    # TextIOBase의 경우 문자열을 반환하므로 인코딩 필요
                    content = value.read()
                    if isinstance(content, str):
                        content = content.encode("utf-8")
                    hasher.update(content)

                    value.seek(current_pos)
                else:
                    hasher.update(f"{key}={value}".encode("utf-8"))
        else:
            hasher.update(str(arg).encode("utf-8"))

    cache_key: str = hasher.hexdigest()
    # logger.debug(f"cache key: %s", cache_key)

    return cache_key


def cache_get(key, default=None, version=None, alias: str = "default"):
    return caches[alias].get(key, default, version)


async def cache_get_async(key, default=None, version=None, alias: str = "default"):
    return await caches[alias].aget(key=key, default=default, version=version)


def cache_set(key, value, timeout=DEFAULT_TIMEOUT, version=None, alias: str = "default"):
    return caches[alias].set(key, value, timeout, version)


async def cache_set_async(key, value, timeout=DEFAULT_TIMEOUT, version=None, alias: str = "default"):
    return await caches[alias].aset(key, value, timeout, version)
