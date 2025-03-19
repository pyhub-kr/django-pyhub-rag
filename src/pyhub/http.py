import logging
from typing import Any, Literal, Optional, Union

import httpx
from asgiref.sync import async_to_sync
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from httpx import URL
from httpx._client import USE_CLIENT_DEFAULT, UseClientDefault  # noqa
from httpx._types import HeaderTypes, RequestData, RequestFiles, TimeoutTypes  # noqa

from pyhub.caches import cache_get_async, cache_make_key, cache_set_async

logger = logging.getLogger(__name__)


async def cached_http_async(
    url: Union[URL, str],
    method: Literal["GET", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"] = "GET",
    headers: Optional[HeaderTypes] = None,
    data: Optional[RequestData] = None,
    files: Optional[RequestFiles] = None,
    timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
    ignore_cache: bool = False,
    cache_alias: str = "default",
    cache_timeout: int = DEFAULT_TIMEOUT,
) -> bytes:
    """
    캐싱을 지원하는 비동기 HTTP POST 요청 함수입니다.

    Raises:
        ValueError: API 호출에 오류가 있는 경우 발생합니다.
    """

    if ignore_cache:
        cache_key = None
    else:
        cache_key = cache_make_key(
            {
                "url": url,
                "method": str(method),
                "headers": headers,
                "data": data,
                "files": files,
            }
        )
        cached_value = await cache_get_async(cache_key, alias=cache_alias)

        if cached_value is None:
            logger.debug("cache[%s] miss : %s - sending request to URL", cache_alias, url)
        else:
            logger.debug("cache[%s] hit : %s - not sending request to URL", cache_alias, url)
            return cached_value

    try:
        async with httpx.AsyncClient() as client:
            logger.debug("request to %s", url)
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                files=files,
                timeout=timeout,
            )
            logger.debug("received response (status code: %d) from %s", response.status_code, url)
            if response.status_code == 200:
                response_data: bytes = response.content
                logger.debug("received response data : %d bytes", len(response_data))

                if cache_key is not None:
                    await cache_set_async(key=cache_key, value=response_data, timeout=cache_timeout, alias=cache_alias)
                    logger.debug("save to cache : %s (%d bytes)", cache_key, len(response.text))

                return response_data
            else:
                raise ValueError(f"Failed: {response.status_code} - {response.text}")
    except httpx.RequestError as e:
        raise ValueError(str(e)) from e
    except httpx.HTTPError as e:
        raise ValueError(str(e)) from e


def cached_http(
    url: Union[URL, str],
    method: Literal["GET", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"] = "GET",
    headers: Optional[HeaderTypes] = None,
    data: Optional[RequestData] = None,
    files: Optional[RequestFiles] = None,
    timeout: Union[TimeoutTypes, UseClientDefault] = USE_CLIENT_DEFAULT,
    ignore_cache: bool = False,
    cache_alias: str = "default",
    cache_timeout: int = DEFAULT_TIMEOUT,
) -> Any:
    return async_to_sync(cached_http_async)(
        url, method, headers, data, files, timeout, ignore_cache, cache_alias, cache_timeout
    )
