import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Optional, Union, cast

from django.core.checks import Error
from django.core.files import File
from django.template import Template
from openai import AsyncOpenAI
from openai import OpenAI as SyncOpenAI

from ..rag.settings import rag_settings
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
        response = sync_client.chat.completions.create(**request_params)
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
        response = await async_client.chat.completions.create(**request_params)
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

        response_stream = sync_client.chat.completions.create(**request_params)
        usage = None

        for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield Reply(text=chunk.choices[0].delta.content)
            if chunk.usage:
                usage = Usage(
                    input=chunk.usage.prompt_tokens or 0,
                    output=chunk.usage.completion_tokens or 0,
                )

        if usage:
            yield Reply(text="", usage=usage)

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

        response_stream = await async_client.chat.completions.create(**request_params)
        usage = None

        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield Reply(text=chunk.choices[0].delta.content)
            if chunk.usage:
                usage = Usage(
                    input=chunk.usage.prompt_tokens or 0,
                    output=chunk.usage.completion_tokens or 0,
                )

        if usage:
            yield Reply(text="", usage=usage)

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

        client = SyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        response = client.embeddings.create(
            input=input,
            model=embedding_model,
        )
        usage = Usage(input=response.usage.prompt_tokens or 0, output=0)
        if isinstance(input, str):
            return Embed(response.data[0].embedding, usage=usage)
        return EmbedList([Embed(v.embedding) for v in response.data], usage=usage)

    async def embed_async(
        self, input: Union[str, list[str]], model: Optional[OpenAIEmbeddingModelType] = None
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(OpenAIEmbeddingModelType, model or self.embedding_model)

        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        response = await client.embeddings.create(
            input=input,
            model=embedding_model,
        )
        usage = Usage(input=response.usage.prompt_tokens or 0, output=0)
        if isinstance(input, str):
            return Embed(response.data[0].embedding, usage=usage)
        return EmbedList([Embed(v.embedding) for v in response.data], usage=usage)


class OpenAILLM(OpenAIMixin, BaseLLM):
    EMBEDDING_DIMENSIONS = {
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
