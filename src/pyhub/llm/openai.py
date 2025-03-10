from typing import Any, AsyncGenerator, Generator, Optional, Union, cast

from django.template import Template
from openai import AsyncOpenAI
from openai import OpenAI as SyncOpenAI

from ..rag.settings import rag_settings
from .base import BaseLLM
from .types import (
    Embed,
    EmbedList,
    LLMChatModel,
    Message,
    OpenAIChatModel,
    OpenAIEmbeddingModel,
    Reply,
    Usage,
)


class OpenAIMixin:

    def _prepare_openai_request(
        self,
        input_context: dict[str, Any],
        messages: list[Message],
        model: LLMChatModel,
    ) -> dict:
        """OpenAI API 요청에 필요한 파라미터를 준비하고 시스템 프롬프트를 처리합니다."""
        message_history = messages.copy()
        system_prompt = self.get_system_prompt(input_context)

        if system_prompt:
            # history에는 system prompt는 누적되지 않고, 매 요청 시마다 적용합니다.
            system_message = Message(role="system", content=system_prompt)
            message_history.insert(0, system_message)

        return {
            "model": model,
            "messages": message_history,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def _make_ask(
        self,
        input_context: dict[str, Any],
        messages: list[Message],
        model: LLMChatModel,
    ) -> Reply:
        sync_client = SyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = self._prepare_openai_request(input_context, messages, model)
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
        messages: list[Message],
        model: LLMChatModel,
    ) -> Reply:
        async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = self._prepare_openai_request(input_context, messages, model)
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
        messages: list[Message],
        model: LLMChatModel,
    ) -> Generator[Reply, None, None]:
        sync_client = SyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = self._prepare_openai_request(input_context, messages, model)
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
        messages: list[Message],
        model: LLMChatModel,
    ) -> AsyncGenerator[Reply, None]:
        async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        request_params = self._prepare_openai_request(input_context, messages, model)
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
        model: Optional[OpenAIChatModel] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
    ) -> Reply:
        return super().ask(
            input,
            model=model,
            context=context,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
        )

    async def ask_async(
        self,
        input: Union[str, dict[str, Any]],
        model: Optional[OpenAIChatModel] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
    ) -> Reply:
        return await super().ask_async(
            input,
            model=model,
            context=context,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
        )

    def embed(
        self, input: Union[str, list[str]], model: Optional[OpenAIEmbeddingModel] = None
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(OpenAIEmbeddingModel, model or self.embedding_model)

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
        self, input: Union[str, list[str]], model: Optional[OpenAIEmbeddingModel] = None
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(OpenAIEmbeddingModel, model or self.embedding_model)

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
        model: OpenAIChatModel = "gpt-4o-mini",
        embedding_model: OpenAIEmbeddingModel = "text-embedding-3-small",
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
