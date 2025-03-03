from typing import AsyncGenerator, Generator, Optional

from openai import AsyncOpenAI
from openai import OpenAI as SyncOpenAI

from pyhub.rag.settings import rag_settings

from .base import BaseLLM
from .types import LLMChatModel, Message, OpenAIChatModel, Reply, Usage


class OpenAILLM(BaseLLM):
    def __init__(
        self,
        model: OpenAIChatModel = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[list[Message]] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            initial_messages=initial_messages,
            api_key=api_key,
        )

    def _prepare_openai_request(self, messages: list[Message], model: LLMChatModel) -> dict:
        history = [*messages]
        if self.system_prompt:
            history.insert(0, {"role": "system", "content": self.system_prompt})

        return {
            "model": model,
            "messages": history,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def _make_reply(self, messages: list[Message], model: LLMChatModel) -> Reply:
        sync_client = SyncOpenAI(api_key=self.api_key or rag_settings.openai_api_key)
        request_params = self._prepare_openai_request(messages, model)
        response = sync_client.chat.completions.create(**request_params)
        return Reply(
            text=response.choices[0].message.content,
            usage=Usage(
                input=response.usage.prompt_tokens or 0,
                output=response.usage.completion_tokens or 0,
            ),
        )

    async def _make_reply_async(self, messages: list[Message], model: LLMChatModel) -> Reply:
        async_client = AsyncOpenAI(api_key=self.api_key or rag_settings.openai_api_key)
        request_params = self._prepare_openai_request(messages, model)
        response = await async_client.chat.completions.create(**request_params)
        return Reply(
            text=response.choices[0].message.content,
            usage=Usage(
                input=response.usage.prompt_tokens or 0,
                output=response.usage.completion_tokens or 0,
            ),
        )

    def _make_reply_stream(self, messages: list[Message], model: LLMChatModel) -> Generator[Reply, None, None]:
        sync_client = SyncOpenAI(api_key=self.api_key or rag_settings.openai_api_key)
        request_params = self._prepare_openai_request(messages, model)
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

    async def _make_reply_stream_async(
        self, messages: list[Message], model: LLMChatModel
    ) -> AsyncGenerator[Reply, None]:
        async_client = AsyncOpenAI(api_key=self.api_key or rag_settings.openai_api_key)
        request_params = self._prepare_openai_request(messages, model)
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

    def reply(
        self,
        human_message: Optional[str] = None,
        model: Optional[OpenAIChatModel] = None,
        stream: bool = False,
    ) -> Reply:
        return super().reply(human_message, model, stream)

    async def areply(
        self,
        human_message: Optional[str] = None,
        model: Optional[OpenAIChatModel] = None,
        stream: bool = False,
    ) -> Reply:
        return await super().areply(human_message, model, stream)
