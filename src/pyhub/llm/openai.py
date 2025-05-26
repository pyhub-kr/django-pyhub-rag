import json
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
    SelectResponse,
    Usage,
)
from .utils.files import FileType, encode_files

logger = logging.getLogger(__name__)


class OpenAIMixin:
    cache_alias = "openai"

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

        return {
            "model": model,
            "messages": message_history,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

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
        )

        response: Optional[ChatCompletion] = None
        if cached_value is not None:
            try:
                response = ChatCompletion.model_validate_json(cached_value)
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            logger.debug("request to openai")
            response: ChatCompletion = sync_client.chat.completions.create(**request_params)
            if cached_value is not None:
                cache_set(cache_key, response.model_dump_json(), alias=self.cache_alias)

        assert response is not None

        return Reply(
            text=response.choices[0].message.content,
            usage=Usage(
                input=response.usage.prompt_tokens or 0,
                output=response.usage.completion_tokens or 0,
            ),
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
        )

        response: Optional[ChatCompletion] = None
        if cached_value is not None:
            try:
                response = ChatCompletion.model_validate_json(cached_value)
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            logger.debug("request to openai")
            response = await async_client.chat.completions.create(**request_params)
            if cache_key is not None:
                await cache_set_async(cache_key, response.model_dump_json(), alias=self.cache_alias)

        assert response is not None

        return Reply(
            text=response.choices[0].message.content,
            usage=Usage(
                input=response.usage.prompt_tokens or 0,
                output=response.usage.completion_tokens or 0,
            ),
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
        )

        if cached_value is not None:
            reply_list = cast(list[Reply], cached_value)
            for reply in reply_list:
                reply.usage = None  # cache 된 응답이기에 usage 내역 제거
                yield reply
        else:
            logger.debug("request to openai")

            response_stream = sync_client.chat.completions.create(**request_params)
            usage = None

            reply_list: list[Reply] = []
            for chunk in response_stream:
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
                reply = Reply(text="", usage=usage)
                reply_list.append(reply)
                yield reply

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
        )

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
                reply = Reply(text="", usage=usage)
                reply_list.append(reply)
                yield reply

            if cache_key is not None:
                await cache_set_async(cache_key, reply_list, alias=self.cache_alias)

    def ask(
        self,
        input: Union[str, dict[str, Any]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[OpenAIChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
    ) -> Reply:
        return super().ask(
            input=input,
            files=files,
            model=model,
            context=context,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
        )

    async def ask_async(
        self,
        input: Union[str, dict[str, Any]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[OpenAIChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
    ) -> Reply:
        return await super().ask_async(
            input=input,
            files=files,
            model=model,
            context=context,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
        )

    def embed(
        self, input: Union[str, list[str]], model: Optional[OpenAIEmbeddingModelType] = None
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(OpenAIEmbeddingModelType, model or self.embedding_model)

        sync_client = SyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = dict(input=input, model=str(embedding_model))

        cache_key, cached_value = cache_make_key_and_get(
            "openai",
            request_params,
            cache_alias=self.cache_alias,
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
        self, input: Union[str, list[str]], model: Optional[OpenAIEmbeddingModelType] = None
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(OpenAIEmbeddingModelType, model or self.embedding_model)

        async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = dict(input=input, model=str(embedding_model))

        cache_key, cached_value = await cache_make_key_and_get_async(
            "openai",
            request_params,
            cache_alias=self.cache_alias,
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

    def _make_select(
        self,
        context: dict[str, Any],
        choices: list[str],
        model: OpenAIChatModelType,
    ) -> SelectResponse:
        """OpenAI의 structured output을 사용한 선택 구현"""
        sync_client = SyncOpenAI(api_key=self.api_key, base_url=self.base_url)

        # JSON Schema 정의
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "selection",
                "schema": {
                    "type": "object",
                    "properties": {
                        "choice": {"type": "string", "enum": choices},
                        "index": {"type": "integer", "minimum": 0, "maximum": len(choices) - 1},
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of why this choice was selected",
                        },
                        "confidence": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Confidence level in the selection",
                        },
                    },
                    "required": ["choice", "index", "reasoning", "confidence"],
                    "additionalProperties": False,
                },
            },
        }

        # 시스템 프롬프트
        allow_none = context.get("allow_none", False)
        system_prompt = """You are a helpful assistant that selects the most appropriate option from a given list.
You must respond with a JSON object containing:
- choice: the exact text of your selected option
- index: the 0-based index of your selection
- reasoning: a brief explanation of your selection
- confidence: your confidence in this selection (0.0 to 1.0)"""

        if allow_none:
            system_prompt += f"\n\nIMPORTANT: {context.get('instruction_none', '')}"

        # 사용자 프롬프트
        user_context = context.get("user_context", "")
        user_prompt = f"""Given the following options:
{context['choices_formatted']}

{f"Context: {user_context}" if user_context else "Select the most appropriate option."}

{f"Note: {context.get('instruction_none', '')}" if allow_none else ""}

Make your selection."""

        # API 호출
        request_params = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.1,  # 선택을 위해 낮은 temperature 사용
            "max_tokens": 200,
            "response_format": response_format,
        }

        # 캐시 확인
        cache_key, cached_value = cache_make_key_and_get(
            "openai_select",
            request_params,
            cache_alias=self.cache_alias,
        )

        if cached_value is not None:
            return cached_value

        try:
            response = sync_client.chat.completions.create(**request_params)

            # 응답 파싱
            result = json.loads(response.choices[0].message.content)

            # Usage 정보 추출
            usage = None
            if response.usage:
                usage = Usage(
                    input=response.usage.prompt_tokens or 0,
                    output=response.usage.completion_tokens or 0,
                )

            select_response = SelectResponse(
                choice=result["choice"], index=result["index"], usage=usage, confidence=result.get("confidence", 1.0)
            )

            # 캐시 저장
            if cache_key is not None:
                cache_set(cache_key, select_response, alias=self.cache_alias)

            return select_response

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response: %s", str(e))
            raise RuntimeError(f"Invalid JSON response from OpenAI: {str(e)}")
        except Exception as e:
            logger.error("Error in OpenAI select: %s", str(e))
            raise
