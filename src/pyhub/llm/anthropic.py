from typing import AsyncGenerator, Generator, Optional, Union

from anthropic import NOT_GIVEN as ANTHROPIC_NOT_GIVEN
from anthropic import Anthropic as SyncAnthropic
from anthropic import AsyncAnthropic

from pyhub.rag.settings import rag_settings

from .base import BaseLLM
from .types import (
    AnthropicChatModel,
    Embed,
    EmbedList,
    Message,
    Reply,
    Usage,
)


class AnthropicLLM(BaseLLM):
    def __init__(
        self,
        model: AnthropicChatModel = "claude-3-5-haiku-latest",
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
            api_key=api_key or rag_settings.anthropic_api_key,
        )

    def _make_ask(
        self,
        messages: list[Message],
        model: AnthropicChatModel,
    ) -> Reply:
        sync_client = SyncAnthropic(api_key=self.api_key)
        response = sync_client.messages.create(
            model=model,
            system=self.system_prompt or ANTHROPIC_NOT_GIVEN,
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        usage = Usage(input=response.usage.input_tokens, output=response.usage.output_tokens)
        return Reply(response.content[0].text, usage)

    async def _make_ask_async(
        self,
        messages: list[Message],
        model: AnthropicChatModel,
    ) -> Reply:
        async_client = AsyncAnthropic(api_key=self.api_key)
        response = await async_client.messages.create(
            model=model,
            system=self.system_prompt or ANTHROPIC_NOT_GIVEN,
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        usage = Usage(input=response.usage.input_tokens, output=response.usage.output_tokens)
        return Reply(response.content[0].text, usage)

    def _make_ask_stream(
        self,
        messages: list[Message],
        model: AnthropicChatModel,
    ) -> Generator[Reply, None, None]:

        sync_client = SyncAnthropic(api_key=self.api_key)
        response = sync_client.messages.create(
            model=model,
            system=self.system_prompt or ANTHROPIC_NOT_GIVEN,
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )

        input_tokens = 0
        output_tokens = 0

        for chunk in response:
            if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                yield Reply(text=chunk.delta.text)
            elif hasattr(chunk, "type") and chunk.type == "content_block_delta":
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    yield Reply(text=chunk.delta.text)
                elif hasattr(chunk, "content_block") and hasattr(chunk.content_block, "text"):
                    yield Reply(text=chunk.content_block.text)

            if hasattr(chunk, "message") and hasattr(chunk.message, "usage"):
                input_tokens += getattr(chunk.message.usage, "input_tokens", None) or 0
                output_tokens += getattr(chunk.message.usage, "output_tokens", None) or 0

            if hasattr(chunk, "usage") and chunk.usage:
                input_tokens += getattr(chunk.usage, "input_tokens", None) or 0
                output_tokens += getattr(chunk.usage, "output_tokens", None) or 0

        yield Reply(text="", usage=Usage(input_tokens, output_tokens))

    async def _make_ask_stream_async(
        self, messages: list[Message], model: AnthropicChatModel
    ) -> AsyncGenerator[Reply, None]:

        async_client = AsyncAnthropic(api_key=self.api_key)
        response = await async_client.messages.create(
            model=model,
            system=self.system_prompt or ANTHROPIC_NOT_GIVEN,
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )

        input_tokens = 0
        output_tokens = 0

        async for chunk in response:
            if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                yield Reply(text=chunk.delta.text)
            elif hasattr(chunk, "type") and chunk.type == "content_block_delta":
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    yield Reply(text=chunk.delta.text)
                elif hasattr(chunk, "content_block") and hasattr(chunk.content_block, "text"):
                    yield Reply(text=chunk.content_block.text)

            if hasattr(chunk, "message") and hasattr(chunk.message, "usage"):
                input_tokens += getattr(chunk.message.usage, "input_tokens", None) or 0
                output_tokens += getattr(chunk.message.usage, "output_tokens", None) or 0

            if hasattr(chunk, "usage") and chunk.usage:
                input_tokens += getattr(chunk.usage, "input_tokens", None) or 0
                output_tokens += getattr(chunk.usage, "output_tokens", None) or 0

        yield Reply(text="", usage=Usage(input_tokens, output_tokens))

    def ask(
        self,
        human_message: str,
        model: Optional[AnthropicChatModel] = None,
        *,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
    ) -> Reply:
        return super().ask(
            human_message,
            model,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
        )

    async def ask_async(
        self,
        human_message: str,
        model: Optional[AnthropicChatModel] = None,
        *,
        stream: bool = False,
        raise_errors: bool = False,
        use_history: bool = True,
    ) -> Reply:
        return await super().ask_async(
            human_message,
            model,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
        )

    def embed(
        self,
        input: Union[str, list[str]],
        model=None,
    ) -> Union[Embed, EmbedList]:
        raise NotImplementedError

    async def embed_async(
        self,
        input: Union[str, list[str]],
        model=None,
    ) -> Union[Embed, EmbedList]:
        raise NotImplementedError


__all__ = ["AnthropicLLM"]
