import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Optional, Union, cast

import pydantic
from django.core.checks import Error
from django.core.files import File
from django.template import Template
from openai import AsyncOpenAI
from openai import OpenAI as SyncOpenAI
from openai.types import CreateEmbeddingResponse
from openai.types.chat import ChatCompletion

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
    OpenAIChatModelType,
    OpenAIEmbeddingModelType,
    Reply,
    Usage,
)
from .utils.files import FileType, encode_files

logger = logging.getLogger(__name__)


class OpenAIMixin:
    cache_alias = "openai"
    supports_stream_options = True  # Override in subclasses if not supported

    def _make_request_params(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OpenAIChatModelType,
        use_files: bool = True,
    ) -> dict:
        """OpenAI API 요청에 필요한 파라미터를 준비하고 시스템 프롬프트를 처리합니다."""
        message_history = [dict(message) for message in messages]
        system_prompt = self.get_system_prompt(input_context)

        if system_prompt:
            # choices가 있으면 시스템 프롬프트에 지시사항 추가
            if "choices" in input_context:
                choices_instruction = (
                    f"\n\nYou must select one option from the given choices: {', '.join(input_context['choices'])}. "
                )
                if input_context.get("allow_none"):
                    choices_instruction += "If none of the options are suitable, you may select 'None of the above'."
                system_prompt += choices_instruction

            # history에는 system prompt는 누적되지 않고, 매 요청 시마다 적용합니다.
            system_message = {"role": "system", "content": system_prompt}
            message_history.insert(0, system_message)

        image_blocks: list[dict] = []

        if use_files:
            # https://platform.openai.com/docs/guides/images?api-mode=chat
            #  - up to 20MB per image
            #  - low resolution : 512px x 512px
            #  - high resolution : 768px (short side) x 2000px (long side)
            image_urls = encode_files(
                human_message.files,
                allowed_types=FileType.IMAGE,
                convert_mode="base64",
            )

            if image_urls:
                for image_url in image_urls:
                    image_blocks.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                                # "detail": "auto",  # low, high, auto (default)
                            },
                        }
                    )
        else:
            if human_message.files:
                logger.warning("Files are ignored because use_files flag is set to False.")

        message_history.append(
            {
                "role": human_message.role,
                "content": [
                    *image_blocks,
                    {"type": "text", "text": human_message.content},
                ],
            }
        )

        request_params = {
            "model": model,
            "messages": message_history,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # choices가 있으면 response_format 추가
        if "choices" in input_context:
            request_params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "choice_response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "choice": {"type": "string", "enum": input_context["choices"]},
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence level in the selection",
                            },
                        },
                        "required": ["choice"],
                        "additionalProperties": False,
                    },
                },
            }
            # structured output을 위해 낮은 temperature 사용
            request_params["temperature"] = 0.1

        return request_params

    def _make_ask(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OpenAIChatModelType,
    ) -> Reply:
        sync_client = SyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = self._make_request_params(
            input_context=input_context,
            human_message=human_message,
            messages=messages,
            model=model,
        )

        cache_key, cached_value = cache_make_key_and_get(
            "openai",
            request_params,
            cache_alias=self.cache_alias,
            enable_cache=input_context.get("enable_cache", False),
        )

        response: Optional[ChatCompletion] = None
        is_cached = False
        if cached_value is not None:
            try:
                response = ChatCompletion.model_validate_json(cached_value)
                is_cached = True
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            logger.debug("request to openai")
            response: ChatCompletion = sync_client.chat.completions.create(**request_params)
            if cache_key is not None:
                cache_set(cache_key, response.model_dump_json(), alias=self.cache_alias)

        assert response is not None

        # 캐시된 응답인 경우 usage를 0으로 설정
        usage_input = 0 if is_cached else (response.usage.prompt_tokens or 0)
        usage_output = 0 if is_cached else (response.usage.completion_tokens or 0)
        
        return Reply(
            text=response.choices[0].message.content,
            usage=Usage(input=usage_input, output=usage_output),
        )

    async def _make_ask_async(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OpenAIChatModelType,
    ) -> Reply:
        async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = self._make_request_params(
            input_context=input_context,
            human_message=human_message,
            messages=messages,
            model=model,
        )

        cache_key, cached_value = await cache_make_key_and_get_async(
            "openai",
            request_params,
            cache_alias=self.cache_alias,
            enable_cache=input_context.get("enable_cache", False),
        )

        response: Optional[ChatCompletion] = None
        is_cached = False
        if cached_value is not None:
            try:
                response = ChatCompletion.model_validate_json(cached_value)
                is_cached = True
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            logger.debug("request to openai")
            response = await async_client.chat.completions.create(**request_params)
            if cache_key is not None:
                await cache_set_async(cache_key, response.model_dump_json(), alias=self.cache_alias)

        assert response is not None

        # 캐시된 응답인 경우 usage를 0으로 설정
        usage_input = 0 if is_cached else (response.usage.prompt_tokens or 0)
        usage_output = 0 if is_cached else (response.usage.completion_tokens or 0)
        
        return Reply(
            text=response.choices[0].message.content,
            usage=Usage(input=usage_input, output=usage_output),
        )

    def _make_ask_stream(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OpenAIChatModelType,
    ) -> Generator[Reply, None, None]:
        sync_client = SyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = self._make_request_params(
            input_context=input_context,
            human_message=human_message,
            messages=messages,
            model=model,
        )
        request_params["stream"] = True

        cache_key, cached_value = cache_make_key_and_get(
            "openai",
            request_params,
            cache_alias=self.cache_alias,
            enable_cache=input_context.get("enable_cache", False),
        )

        # Add stream_options after cache key generation (if supported)
        if self.supports_stream_options:
            request_params["stream_options"] = {"include_usage": True}

        if cached_value is not None:
            logger.debug("Using cached response - usage info will not be available")
            reply_list = cast(list[Reply], cached_value)
            for reply in reply_list:
                reply.usage = None  # cache 된 응답이기에 usage 내역 제거
                yield reply
        else:
            logger.debug(
                "Request to %s (supports_stream_options=%s, stream_options=%s)",
                self.__class__.__name__,
                self.supports_stream_options,
                request_params.get("stream_options"),
            )

            response_stream = sync_client.chat.completions.create(**request_params)
            usage = None

            reply_list: list[Reply] = []
            chunk_count = 0
            for chunk in response_stream:
                chunk_count += 1
                if chunk.choices and chunk.choices[0].delta.content:  # noqa
                    reply = Reply(text=chunk.choices[0].delta.content)
                    reply_list.append(reply)
                    yield reply
                if chunk.usage:
                    logger.debug(
                        "Found usage in sync stream: input=%s, output=%s",
                        chunk.usage.prompt_tokens,
                        chunk.usage.completion_tokens,
                    )
                    usage = Usage(
                        input=chunk.usage.prompt_tokens or 0,
                        output=chunk.usage.completion_tokens or 0,
                    )

            logger.debug("Processed %d chunks from OpenAI stream", chunk_count)
            if usage:
                logger.debug(
                    "Yielding final usage chunk with usage info: input=%d, output=%d", usage.input, usage.output
                )
                reply = Reply(text="", usage=usage)
                reply_list.append(reply)
                yield reply
            else:
                if self.supports_stream_options:
                    logger.warning(
                        "No usage information received from %s stream despite stream_options", self.__class__.__name__
                    )
                else:
                    logger.debug(
                        "No usage information received from %s stream (stream_options not supported)",
                        self.__class__.__name__,
                    )

            if cache_key is not None:
                cache_set(cache_key, reply_list, alias=self.cache_alias)

    async def _make_ask_stream_async(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: OpenAIChatModelType,
    ) -> AsyncGenerator[Reply, None]:
        async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = self._make_request_params(
            input_context=input_context,
            human_message=human_message,
            messages=messages,
            model=model,
        )
        request_params["stream"] = True

        cache_key, cached_value = await cache_make_key_and_get_async(
            "openai",
            request_params,
            cache_alias=self.cache_alias,
            enable_cache=input_context.get("enable_cache", False),
        )

        # Add stream_options after cache key generation (if supported)
        if self.supports_stream_options:
            request_params["stream_options"] = {"include_usage": True}

        if cached_value is not None:
            reply_list = cast(list[Reply], cached_value)
            for reply in reply_list:
                reply.usage = None  # cache 된 응답이기에 usage 내역 제거
                yield reply
        else:
            logger.debug("request to openai")

            response_stream = await async_client.chat.completions.create(**request_params)
            usage = None

            reply_list: list[Reply] = []
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:  # noqa
                    reply = Reply(text=chunk.choices[0].delta.content)
                    reply_list.append(reply)
                    yield reply
                if chunk.usage:
                    usage = Usage(
                        input=chunk.usage.prompt_tokens or 0,
                        output=chunk.usage.completion_tokens or 0,
                    )

            if usage:
                logger.debug(
                    "Yielding final usage chunk with usage info: input=%d, output=%d", usage.input, usage.output
                )
                reply = Reply(text="", usage=usage)
                reply_list.append(reply)
                yield reply
            else:
                if self.supports_stream_options:
                    logger.warning(
                        "No usage information received from %s stream despite stream_options", self.__class__.__name__
                    )
                else:
                    logger.debug(
                        "No usage information received from %s stream (stream_options not supported)",
                        self.__class__.__name__,
                    )

            if cache_key is not None:
                await cache_set_async(cache_key, reply_list, alias=self.cache_alias)

    def ask(
        self,
        input: Union[str, dict[str, Any]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[OpenAIChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        choices: Optional[list[str]] = None,
        choices_optional: bool = False,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
        enable_cache: bool = False,
    ) -> Union[Reply, Generator[Reply, None, None]]:
        return super().ask(
            input=input,
            files=files,
            model=model,
            context=context,
            choices=choices,
            choices_optional=choices_optional,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
            enable_cache=enable_cache,
        )

    async def ask_async(
        self,
        input: Union[str, dict[str, Any]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[OpenAIChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        choices: Optional[list[str]] = None,
        choices_optional: bool = False,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
        enable_cache: bool = False,
    ) -> Union[Reply, AsyncGenerator[Reply, None]]:
        return await super().ask_async(
            input=input,
            files=files,
            model=model,
            context=context,
            choices=choices,
            choices_optional=choices_optional,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
            enable_cache=enable_cache,
        )

    def embed(
        self, input: Union[str, list[str]], model: Optional[OpenAIEmbeddingModelType] = None, enable_cache: bool = False
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(OpenAIEmbeddingModelType, model or self.embedding_model)

        sync_client = SyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = dict(input=input, model=str(embedding_model))

        cache_key, cached_value = cache_make_key_and_get(
            "openai",
            request_params,
            cache_alias=self.cache_alias,
            enable_cache=enable_cache,
        )

        response: Optional[CreateEmbeddingResponse] = None
        if cached_value is not None:
            response = cast(CreateEmbeddingResponse, cached_value)
            response.usage.prompt_tokens = 0  # 캐싱된 응답이기에 clear usage
            response.usage.completion_tokens = 0

        if response is None:
            logger.debug("request to openai")
            response = sync_client.embeddings.create(**request_params)
            if cache_key is not None:
                cache_set(cache_key, response, alias=self.cache_alias)

        assert response is not None

        usage = Usage(input=response.usage.prompt_tokens or 0, output=0)
        if isinstance(input, str):
            return Embed(response.data[0].embedding, usage=usage)
        return EmbedList([Embed(v.embedding) for v in response.data], usage=usage)

    async def embed_async(
        self, input: Union[str, list[str]], model: Optional[OpenAIEmbeddingModelType] = None, enable_cache: bool = False
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(OpenAIEmbeddingModelType, model or self.embedding_model)

        async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = dict(input=input, model=str(embedding_model))

        cache_key, cached_value = await cache_make_key_and_get_async(
            "openai",
            request_params,
            cache_alias=self.cache_alias,
            enable_cache=enable_cache,
        )

        response: Optional[CreateEmbeddingResponse] = None
        if cached_value is not None:
            response = cast(CreateEmbeddingResponse, cached_value)
            response.usage.prompt_tokens = 0  # 캐싱된 응답이기에 clear usage
            response.usage.completion_tokens = 0

        if response is None:
            logger.debug("request to openai")
            response = await async_client.embeddings.create(**request_params)
            if cache_key is not None:
                await cache_set_async(cache_key, response, alias=self.cache_alias)

        assert response is not None

        usage = Usage(input=response.usage.prompt_tokens or 0, output=0)
        if isinstance(input, str):
            return Embed(response.data[0].embedding, usage=usage)
        return EmbedList([Embed(v.embedding) for v in response.data], usage=usage)


class OpenAILLM(OpenAIMixin, BaseLLM):
    EMBEDDING_DIMENSIONS = {
        "text-embedding-ada-002": 1536,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "embedding-query": 4096,
        "embedding-passage": 4096,
    }

    def __init__(
        self,
        model: OpenAIChatModelType = "gpt-4o-mini",
        embedding_model: OpenAIEmbeddingModelType = "text-embedding-3-small",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[Union[str, Template]] = None,
        prompt: Optional[Union[str, Template]] = None,
        output_key: str = "text",
        initial_messages: Optional[list[Message]] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(
            model=model,
            embedding_model=embedding_model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            prompt=prompt,
            output_key=output_key,
            initial_messages=initial_messages,
            api_key=api_key or rag_settings.openai_api_key,
        )
        self.base_url = base_url or rag_settings.openai_base_url

    def check(self) -> list[Error]:
        errors = super().check()

        if not self.api_key or not self.api_key.startswith("sk-"):
            errors.append(
                Error(
                    "OpenAI API key is not set or is invalid.",
                    hint="Please check your OpenAI API key.",
                    obj=self,
                )
            )

        return errors
