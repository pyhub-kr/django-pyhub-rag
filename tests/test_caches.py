from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile
from django.test import TestCase

from pyhub.caches import (
    cache_clear,
    cache_clear_async,
    cache_get,
    cache_get_async,
    cache_make_key,
    cache_make_key_and_get,
    cache_make_key_and_get_async,
    cache_set,
    cache_set_async,
)


@pytest.mark.django_db
class TestCaches(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cache_clear()

    @classmethod
    def tearDownClass(cls):
        cache_clear()
        super().tearDownClass()

    def test_cache_clear(self):
        # 캐시에 데이터 설정
        cache_set("test_key", "test_value")
        assert cache_get("test_key") == "test_value"

        # 캐시 클리어
        cache_clear()
        assert cache_get("test_key") is None

    @pytest.mark.asyncio
    async def test_cache_clear_async(self):
        # 캐시에 데이터 설정
        await cache_set_async("test_key", "test_value")
        assert await cache_get_async("test_key") == "test_value"

        # 캐시 클리어
        await cache_clear_async()
        assert await cache_get_async("test_key") is None

    def test_cache_make_key_with_simple_args(self):
        # 간단한 인자로 키 생성
        key1 = cache_make_key({"a": 1, "b": "test", "c": 3.14})
        key2 = cache_make_key({"a": 1, "b": "test", "c": 3.14})
        key3 = cache_make_key({"a": 1, "b": "different", "c": 3.14})

        assert key1 == key2
        assert key1 != key3

    def test_cache_make_key_with_dict(self):
        # 딕셔너리 인자로 키 생성
        key1 = cache_make_key({"a": 1, "b": 2})
        key2 = cache_make_key({"b": 2, "a": 1})
        key3 = cache_make_key({"a": 1, "b": 3})

        assert key1 == key2
        assert key1 != key3

    def test_cache_make_key_with_file(self):
        # 파일 객체를 포함한 인자로 키 생성
        file1 = ContentFile(b"test content")
        file2 = ContentFile(b"test content")
        file3 = ContentFile(b"different content")

        key1 = cache_make_key({"file": file1})
        key2 = cache_make_key({"file": file2})
        key3 = cache_make_key({"file": file3})

        assert key1 == key2
        assert key1 != key3

    def test_cache_make_key_with_chat_messages(self):
        cache_make_key(
            {
                "max_tokens": 1000,
                "messages": [
                    {"content": "hello. my name is tom.", "role": "user"},
                    {"content": "Hello, Tom! How can I assist you today?", "role": "assistant"},
                    {"content": [{"text": "what is my name?", "type": "text"}], "role": "user"},
                ],
                "model": "gpt-4o-mini",
                "temperature": 0.2,
                "type": "openai",
            }
        )

    def test_cache_get_set(self):
        # 캐시 설정 및 조회
        cache_set("test_key", "test_value")
        assert cache_get("test_key") == "test_value"

        # 존재하지 않는 키
        assert cache_get("non_existent_key") is None
        assert cache_get("non_existent_key", "default_value") == "default_value"

    @pytest.mark.asyncio
    async def test_cache_get_set_async(self):
        # 비동기 캐시 설정 및 조회
        await cache_set_async("test_key", "test_value")
        assert await cache_get_async("test_key") == "test_value"

        # 존재하지 않는 키
        assert await cache_get_async("non_existent_key") is None
        assert await cache_get_async("non_existent_key", "default_value") == "default_value"

    @patch("pyhub.caches.cache_get")
    def test_cache_make_key_and_get_hit(self, mock_cache_get):
        # 캐시 히트 시나리오
        mock_client = MagicMock()
        mock_client.base_url = "https://test.com"
        mock_cache_get.return_value = b"cached_data"

        cache_key, cached_value = cache_make_key_and_get("test_type", mock_client, {"key": "value"})

        assert cached_value == b"cached_data"
        mock_cache_get.assert_called_once()

    @patch("pyhub.caches.cache_get")
    def test_cache_make_key_and_get_miss(self, mock_cache_get):
        # 캐시 미스 시나리오
        mock_client = MagicMock()
        mock_client.base_url = "https://test.com"
        mock_cache_get.return_value = None

        cache_key, cached_value = cache_make_key_and_get("test_type", mock_client, {"key": "value"})

        assert cached_value is None
        mock_cache_get.assert_called_once()

    @pytest.mark.asyncio
    @patch("pyhub.caches.cache_get_async")
    async def test_cache_make_key_and_get_async_hit(self, mock_cache_get):
        # 캐시 히트 시나리오
        mock_client = MagicMock()
        mock_client.base_url = "https://test.com"
        mock_cache_get.return_value = b"cached_data"

        cache_key, cached_value = await cache_make_key_and_get_async("test_type", mock_client, {"key": "value"})

        assert cached_value == b"cached_data"
        mock_cache_get.assert_called_once()

    @pytest.mark.asyncio
    @patch("pyhub.caches.cache_get_async")
    async def test_cache_make_key_and_get_async_miss(self, mock_cache_get):
        # 캐시 미스 시나리오
        mock_client = MagicMock()
        mock_client.base_url = "https://test.com"
        mock_cache_get.return_value = None

        cache_key, cached_value = await cache_make_key_and_get_async("test_type", mock_client, {"key": "value"})

        assert cached_value is None
        mock_cache_get.assert_called_once()
