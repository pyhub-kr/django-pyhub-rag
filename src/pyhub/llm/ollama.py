import logging
import re
from typing import Any, AsyncGenerator, Generator, Optional, Union, cast

import pydantic
from django.core.checks import Error
from django.template import Template
from ollama import AsyncClient, ChatResponse
from ollama import Client as SyncClient
from ollama import EmbedResponse, ListResponse
from pydantic import ValidationError

from pyhub.caches import (
    cache_make_key_and_get,
    cache_make_key_and_get_async,
    cache_set,
    cache_set_async,
)
from pyhub.rag.settings import rag_settings

from .base import BaseLLM
from .types import (
    Embed,
    EmbedList,
    Message,
    OllamaChatModelType,
    OllamaEmbeddingModelType,
    Reply,
)
from .utils.files import FileType, encode_files

logger = logging.getLogger(__name__)


class OllamaLLM(BaseLLM):
    """
    Ollama API를 사용하여 LLM 기능을 제공하는 클래스입니다.
    """

    EMBEDDING_DIMENSIONS = {
        "nomic-embed-text": 768,
        "avr/sfr-embedding-mistral": 4096,
    }

    def __init__(
        self,
        model: OllamaChatModelType = "mistral",
        embedding_model: OllamaEmbeddingModelType = "nomic-embed-text",
        temperature: float = 0.2,
        # max_tokens: int = 1000,
        system_prompt: Optional[Union[str, Template]] = None,
        prompt: Optional[Union[str, Template]] = None,
        output_key: str = "text",
        initial_messages: Optional[list[Message]] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
    ):
        """
        Ollama LLM 클래스 초기화

        Args:
            model: 사용할 Ollama 모델 이름
            embedding_model: 임베딩에 사용할 모델 이름
            temperature: 생성 다양성 조절 (0.0-1.0)
            system_prompt: 시스템 프롬프트
            prompt: 사용자 프롬프트 템플릿
            output_key: 출력 결과를 저장할 키
            initial_messages: 초기 대화 메시지 목록
            base_url: Ollama API 기본 URL
            timeout: API 요청 타임아웃 (초)
        """

        if ":" not in model:
            model += ":latest"

        if ":" not in embedding_model:
            embedding_model += ":latest"

        super().__init__(
            model=model,
            embedding_model=embedding_model,
            temperature=temperature,
            # max_tokens=max_tokens,
            system_prompt=system_prompt,
            prompt=prompt,
            output_key=output_key,
            initial_messages=initial_messages,
        )
        self.base_url = base_url or rag_settings.ollama_base_url
        self.timeout = timeout

    def check(self) -> list[Error]:
        errors = super().check()

        def add_error(msg: str, hint: str = None):
            errors.append(Error(msg, hint=hint, obj=self))

        client = SyncClient(host=self.base_url)
        try:
            response: ListResponse = client.list()
        except ConnectionError:
            add_error(f"Unable to connect to Ollama server at {self.base_url}.")
        else:
            model_name_set = {model.model for model in response.models}

            if self.model not in model_name_set:
                add_error(
                    f"Ollama model '{self.model}' not found on server at {self.base_url}",
                    hint="Please check if the model is installed or use 'ollama pull {self.model}' to download it.",
                )

            if self.embedding_model not in model_name_set:
                add_error(
                    f"Ollama embedding model '{self.embedding_model}' not found on server at {self.base_url}",
                    hint="Please check if the embedding model is installed or use 'ollama pull {self.embedding_model}' to download it.",
                )

        return errors

    def _make_request_params(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OllamaChatModelType,
    ) -> dict:
        """Ollama API 요청에 필요한 파라미터를 준비하고 시스템 프롬프트를 처리합니다."""
        message_history = [dict(message) for message in messages]
        system_prompt = self.get_system_prompt(input_context)

        if system_prompt:
            # history에는 system prompt는 누적되지 않고, 매 요청 시마다 적용합니다.
            system_message = {"role": "system", "content": system_prompt}
            message_history.insert(0, system_message)

        # https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-completion
        image_urls = encode_files(
            human_message.files,
            allowed_types=FileType.IMAGE,
            convert_mode="base64",
        )

        if image_urls:
            base64_url_pattern = r"^data:([^;]+);base64,(.+)"

            b64_str_list: list[str] = []
            for image_url in image_urls:
                base64_url_match = re.match(base64_url_pattern, image_url)
                if base64_url_match:
                    # mimetype = base64_url_match.group(1)
                    b64_str = base64_url_match.group(2)
                    b64_str_list.append(b64_str)

            message_history.append(
                {
                    "role": human_message.role,
                    "content": human_message.content,
                    "images": b64_str_list,
                }
            )
        else:
            message_history.append(
                {
                    "role": human_message.role,
                    "content": human_message.content,
                }
            )

        logger.debug("Ollama model: %s, temperature: %s", model, self.temperature)

        return {
            "model": model,
            "messages": message_history,
            "options": {
                "temperature": self.temperature,
                #  "max_tokens": self.max_tokens,  # ollama 에서는 미지원
            },
        }

    def _make_ask(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OllamaChatModelType,
    ) -> Reply:
        """
        Ollama API를 사용하여 동기적으로 응답을 생성합니다.
        """

        sync_client = SyncClient(host=self.base_url)
        request_params = self._make_request_params(
            input_context=input_context,
            human_message=human_message,
            messages=messages,
            model=model,
        )

        cache_key, cached_value = cache_make_key_and_get(
            "ollama",
            request_params,
            cache_alias="ollama",
        )

        response: Optional[ChatResponse] = None
        if cached_value is not None:
            try:
                response = ChatResponse.model_validate_json(cached_value)
            except ValidationError:
                logger.error("Invalid cached value : %s", cached_value)

        if response is None:
            logger.debug("request to ollama")
            response = sync_client.chat(**request_params)
            cache_set(cache_key, response.model_dump_json(), alias="ollama")

        assert response is not None
        return Reply(text=response.message.content)

    async def _make_ask_async(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OllamaChatModelType,
    ) -> Reply:
        """
        Ollama API를 사용하여 비동기적으로 응답을 생성합니다.
        """

        async_client = AsyncClient(host=self.base_url)
        request_params = self._make_request_params(
            input_context=input_context,
            human_message=human_message,
            messages=messages,
            model=model,
        )

        cache_key, cached_value = await cache_make_key_and_get_async(
            "ollama",
            request_params,
            cache_alias="ollama",
        )
        response: Optional[ChatResponse] = None
        if cached_value is not None:
            try:
                response = ChatResponse.model_validate_json(cached_value)
            except ValidationError:
                logger.error("Invalid cached value : %s", cached_value)
                cached_value = None

        if cached_value is None:
            logger.debug("request to ollama")
            response: ChatResponse = await async_client.chat(**request_params)
            await cache_set_async(cache_key, response.model_dump_json(), alias="ollama")

        assert response is not None
        return Reply(text=response.message.content)

    def _make_ask_stream(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OllamaChatModelType,
    ) -> Generator[Reply, None, None]:
        """
        Ollama API를 사용하여 동기적으로 스트리밍 응답을 생성합니다.
        """

        sync_client = SyncClient(host=self.base_url)
        request_params = self._make_request_params(
            input_context=input_context,
            human_message=human_message,
            messages=messages,
            model=model,
        )
        request_params["stream"] = True

        cache_key, cached_value = cache_make_key_and_get(
            "ollama",
            request_params,
            cache_alias="ollama",
        )

        if cached_value is not None:
            reply_list = cast(list[Reply], cached_value)
            for reply in reply_list:
                yield reply
        else:
            logger.debug("request to ollama")

            response_stream = sync_client.chat(**request_params)

            reply_list: list[Reply] = []
            for chunk in response_stream:
                reply = Reply(text=chunk.message.content or "")
                reply_list.append(reply)
                yield reply

            cache_set(cache_key, reply_list, alias="ollama")

    async def _make_ask_stream_async(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OllamaChatModelType,
    ) -> AsyncGenerator[Reply, None]:
        """
        Ollama API를 사용하여 비동기적으로 스트리밍 응답을 생성합니다.
        """
        async_client = AsyncClient(host=self.base_url)
        request_params = self._make_request_params(
            input_context=input_context,
            human_message=human_message,
            messages=messages,
            model=model,
        )
        request_params["stream"] = True

        cache_key, cached_value = await cache_make_key_and_get_async(
            "ollama",
            request_params,
            cache_alias="ollama",
        )
        if cached_value is not None:
            reply_list = cast(list[Reply], cached_value)
            for reply in reply_list:
                yield reply
        else:
            logger.debug("request to ollama")

            response = await async_client.chat(**request_params)

            reply_list: list[Reply] = []
            async for chunk in response:
                reply = Reply(text=chunk.message.content or "")
                reply_list.append(reply)
                yield reply

            await cache_set_async(cache_key, reply_list, alias="ollama")

    def embed(
        self,
        input: Union[str, list[str]],
        model: Optional[OllamaEmbeddingModelType] = None,
    ) -> Union[Embed, EmbedList]:
        """
        Ollama API를 사용하여 텍스트를 임베딩합니다.
        """
        embedding_model = model or self.embedding_model

        sync_client = SyncClient(host=self.base_url)
        request_params = dict(
            model=cast(str, embedding_model),
            input=input,
        )

        cache_key, cached_value = cache_make_key_and_get(
            "ollama",
            request_params,
            cache_alias="ollama",
        )

        response: Optional[EmbedResponse] = None
        if cached_value is not None:
            try:
                response = EmbedResponse.model_validate_json(cached_value)
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            logger.debug("request to ollama")
            response = sync_client.embed(**request_params)
            cache_set(cache_key, response.model_dump_json(), alias="ollama")

        if isinstance(input, str):
            return Embed(list(response.embeddings[0]))
        return EmbedList([Embed(list(e)) for e in response.embeddings])

    async def embed_async(
        self,
        input: Union[str, list[str]],
        model: Optional[str] = None,
    ) -> Union[Embed, EmbedList]:
        """
        Ollama API를 사용하여 비동기적으로 텍스트를 임베딩합니다.
        """

        embedding_model = model or self.embedding_model

        async_client = AsyncClient(host=self.base_url)
        request_params = dict(
            model=cast(str, embedding_model),
            input=input,
        )

        cache_key, cached_value = await cache_make_key_and_get_async(
            "ollama",
            request_params,
            cache_alias="ollama",
        )

        response: Optional[EmbedResponse] = None
        if cached_value is not None:
            try:
                response = EmbedResponse.model_validate_json(cached_value)
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            logger.debug("request to ollama")
            response = await async_client.embed(**request_params)
            await cache_set_async(cache_key, response.model_dump_json(), alias="ollama")

        if isinstance(input, str):
            return Embed(list(response.embeddings[0]))
        return EmbedList([Embed(list(e)) for e in response.embeddings])


__all__ = ["OllamaLLM"]
