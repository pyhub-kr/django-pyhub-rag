import logging
from hashlib import md5
from io import IOBase
from typing import Any, Optional, Union

from django.core.cache import caches
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.files import File

logger = logging.getLogger(__name__)


def cache_clear(alias: str = "default") -> None:
    logger.info("cache[%s] clear", alias)
    caches[alias].clear()


def cache_clear_all():
    for cache_alias in caches:
        logger.info("cache[%s] clear", cache_alias)
        caches[cache_alias].clear()


async def cache_clear_async(alias: str = "default") -> None:
    await caches[alias].aclear()


class CacheKeyMaker:
    def __init__(self):
        self.hasher = md5()

    def _handle_dict(self, arg_value: dict[str, Any]) -> None:
        for key in sorted(arg_value.keys()):
            self.hasher.update(key.encode())
            value = arg_value[key]
            self._handle(value)

    def _handle_sequence(self, arg_value: Union[list, tuple]) -> None:
        for item in arg_value:
            self._handle(item)

    def _handle_file(self, file_obj: Union[File, IOBase]) -> None:
        current_pos = file_obj.tell()
        file_obj.seek(0)
        content = file_obj.read()
        file_obj.seek(current_pos)

        if isinstance(content, str):
            content = content.encode("utf-8")
        self.hasher.update(content)

    def _handle(self, v: Any):
        if isinstance(v, dict):
            self._handle_dict(v)
        elif isinstance(v, (list, tuple)):
            self._handle_sequence(v)
        elif isinstance(v, (File, IOBase)):
            self._handle_file(v)
        else:
            self.hasher.update(str(v).encode("utf-8"))

    def make_key(
        self,
        kwargs: dict[
            str,
            Union[
                int,
                float,
                str,
                dict[str, Union[str, int, File, IOBase]],
                tuple[str, Any],
                File,
                IOBase,
            ],
        ],
    ) -> str:
        """
        주어진 인자들을 기반으로 캐시 키를 생성합니다.

        Args:
            kwargs (dict): 캐시 키 생성에 사용할 인자 리스트

        Returns:
            str: 캐시 키 문자열
        """
        converted_kwargs = convert_dict_to_tuple(kwargs)

        for arg in sorted(converted_kwargs):
            self._handle(arg)

        cache_key: str = self.hasher.hexdigest()
        logger.debug("cache key: %s", cache_key)

        return cache_key


def cache_make_key(
    kwargs: dict[
        str,
        Union[
            int,
            float,
            str,
            dict[str, Union[str, int, File, IOBase]],
            tuple[str, Any],
            File,
            IOBase,
        ],
    ],
) -> str:
    """
    주어진 인자들을 기반으로 캐시 키를 생성합니다.

    Args:
        kwargs (dict): 캐시 키 생성에 사용할 인자 리스트

    Returns:
        str: 캐시 키 문자열
    """
    key_maker = CacheKeyMaker()
    return key_maker.make_key(kwargs)


def cache_get(key, default=None, version=None, alias: str = "default"):
    # TODO: cache 이전이 완료되었다고 판단이 될 때 제거하기
    if alias != "default":
        v = caches["default"].get(key, default, version)
        if v is not None:
            return v

    return caches[alias].get(key, default, version)


async def cache_get_async(key, default=None, version=None, alias: str = "default"):
    # TODO: cache 이전이 완료되었다고 판단이 될 때 제거하기
    if alias != "default":
        v = await caches["default"].aget(key, default, version)
        if v is not None:
            return v

    return await caches[alias].aget(key=key, default=default, version=version)


def cache_set(key, value, timeout=DEFAULT_TIMEOUT, version=None, alias: str = "default"):
    return caches[alias].set(key, value, timeout, version)


async def cache_set_async(key, value, timeout=DEFAULT_TIMEOUT, version=None, alias: str = "default"):
    return await caches[alias].aset(key, value, timeout, version)


async def cache_make_key_and_get_async(
    type: str,
    kwargs: dict[
        str,
        Union[
            int,
            float,
            str,
            dict[str, Union[str, int, IOBase]],
        ],
    ],
    cache_alias: str = "default",
) -> tuple[str, Optional[bytes]]:

    key_args = dict(type=type, **kwargs)
    cache_key = cache_make_key(key_args)
    cached_value = await cache_get_async(cache_key, alias=cache_alias)

    if cached_value is None:
        logger.debug("cache[%s] miss : sending api request", cache_alias)
    else:
        logger.debug("cache[%s] hit : not sending api request", cache_alias)

    return cache_key, cached_value


def cache_make_key_and_get(
    type: str,
    kwargs: dict[
        str,
        Union[
            int,
            float,
            str,
            dict[str, Union[str, int, IOBase]],
        ],
    ],
    cache_alias: str = "default",
) -> tuple[str, Optional[bytes]]:
    key_args = dict(type=type, **kwargs)
    cache_key = cache_make_key(key_args)
    cached_value = cache_get(cache_key, alias=cache_alias)

    if cached_value is None:
        logger.debug("cache[%s] miss : sending api request", cache_alias)
    else:
        logger.debug("cache[%s] hit : not sending api request", cache_alias)

    return cache_key, cached_value


def convert_dict_to_tuple(d: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    """
    딕셔너리를 튜플로 변환하는 함수
    내부에 딕셔너리가 있으면 재귀적으로 변환
    """
    return tuple((key, convert_dict_to_tuple(value) if isinstance(value, dict) else value) for key, value in d.items())
