from typing import AsyncGenerator, Generator, Optional, Union, Any

from anthropic import NOT_GIVEN as ANTHROPIC_NOT_GIVEN
from anthropic import Anthropic as SyncAnthropic
from anthropic import AsyncAnthropic
from django.core.checks import Error
from django.template import Template

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
        system_prompt: Optional[Union[str, Template]] = None,
        prompt: Optional[Union[str, Template]] = None,
        output_key: str = "text",
        initial_messages: Optional[list[Message]] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            prompt=prompt,
            output_key=output_key,
            initial_messages=initial_messages,
            api_key=api_key or rag_settings.anthropic_api_key,
        )

    def check(self) -> list[Error]:
        errors = super().check()

        if not self.api_key or not self.api_key.startswith("sk-ant-"):
            errors.append(
                Error(
                    "Anthropic API key is not set or is invalid.",
                    hint="Please check your Anthropic API key.",
                    obj=self,
                )
            )

        return errors

    async def _make_ask_async(
        self,
        input_context: dict[str, Any],
        messages: list[Message],
        model: AnthropicChatModel,
    ) -> Reply:
        async_client = AsyncAnthropic(api_key=self.api_key)
        response = await async_client.messages.create(
            model=model,
            system=self.get_system_prompt(input_context, default=ANTHROPIC_NOT_GIVEN),
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        usage = Usage(input=response.usage.input_tokens, output=response.usage.output_tokens)
        return Reply(response.content[0].text, usage)

    def _make_ask(
        self,
        input_context: dict[str, Any],
        messages: list[Message],
        model: AnthropicChatModel,
    ) -> Reply:
        sync_client = SyncAnthropic(api_key=self.api_key)
        response = sync_client.messages.create(
            model=model,
            system=self.get_system_prompt(input_context, default=ANTHROPIC_NOT_GIVEN),
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        usage = Usage(input=response.usage.input_tokens, output=response.usage.output_tokens)
        return Reply(response.content[0].text, usage)

    def _make_ask_stream(
        self,
        input_context: dict[str, Any],
        messages: list[Message],
        model: AnthropicChatModel,
    ) -> Generator[Reply, None, None]:

        sync_client = SyncAnthropic(api_key=self.api_key)
        response = sync_client.messages.create(
            model=model,
            system=self.get_system_prompt(input_context, default=ANTHROPIC_NOT_GIVEN),
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
        self, input_context: dict[str, Any], messages: list[Message], model: AnthropicChatModel
    ) -> AsyncGenerator[Reply, None]:

        async_client = AsyncAnthropic(api_key=self.api_key)
        response = await async_client.messages.create(
            model=model,
            system=self.get_system_prompt(input_context, default=ANTHROPIC_NOT_GIVEN),
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
        input: Union[str, dict[str, Any]],
        model: Optional[AnthropicChatModel] = None,
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
        model: Optional[AnthropicChatModel] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        stream: bool = False,
        raise_errors: bool = False,
        use_history: bool = True,
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
