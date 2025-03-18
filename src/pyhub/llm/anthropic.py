import re
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Optional, Union

from anthropic import NOT_GIVEN as ANTHROPIC_NOT_GIVEN
from anthropic import Anthropic as SyncAnthropic
from anthropic import AsyncAnthropic
from django.core.checks import Error
from django.core.files import File
from django.template import Template

from pyhub.rag.settings import rag_settings

from .base import BaseLLM
from .types import (
    AnthropicChatModelType,
    Embed,
    EmbedList,
    Message,
    Reply,
    Usage,
)
from .utils.files import FileType, encode_files


class AnthropicLLM(BaseLLM):
    def __init__(
        self,
        model: AnthropicChatModelType = "claude-3-5-haiku-latest",
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

    def _make_request_params(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: AnthropicChatModelType,
    ) -> dict:
        message_history = [dict(message) for message in messages]

        # https://docs.anthropic.com/en/docs/build-with-claude/vision
        image_urls = encode_files(
            human_message.files,
            allowed_types=FileType.IMAGE,
            convert_mode="base64",
        )

        image_blocks: list[dict] = []
        if image_urls:
            base64_url_pattern = r"^data:([^;]+);base64,(.+)"

            for image_url in image_urls:
                base64_url_match = re.match(base64_url_pattern, image_url)
                if base64_url_match:
                    mimetype = base64_url_match.group(1)
                    b64_str = base64_url_match.group(2)
                    image_blocks.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mimetype,
                                "data": b64_str,
                            },
                        }
                    )
                else:
                    image_blocks.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "url",
                                "url": image_url,
                            },
                        }
                    )

        message_history.append(
            {
                "role": human_message.role,
                "content": [
                    *image_blocks,
                    {"type": "text", "text": human_message.content},
                ],
            }
        )

        return dict(
            model=model,
            system=self.get_system_prompt(input_context, default=ANTHROPIC_NOT_GIVEN),
            messages=message_history,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def _make_ask_async(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: AnthropicChatModelType,
    ) -> Reply:
        async_client = AsyncAnthropic(api_key=self.api_key)
        request_params = self._make_request_params(
            input_context=input_context, human_message=human_message, messages=messages, model=model
        )
        response = await async_client.messages.create(**request_params)
        usage = Usage(input=response.usage.input_tokens, output=response.usage.output_tokens)
        return Reply(response.content[0].text, usage)

    def _make_ask(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: AnthropicChatModelType,
    ) -> Reply:
        sync_client = SyncAnthropic(api_key=self.api_key)
        request_params = self._make_request_params(
            input_context=input_context, human_message=human_message, messages=messages, model=model
        )
        response = sync_client.messages.create(**request_params)
        usage = Usage(input=response.usage.input_tokens, output=response.usage.output_tokens)
        return Reply(response.content[0].text, usage)

    def _make_ask_stream(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: AnthropicChatModelType,
    ) -> Generator[Reply, None, None]:

        sync_client = SyncAnthropic(api_key=self.api_key)
        request_params = self._make_request_params(
            input_context=input_context, human_message=human_message, messages=messages, model=model
        )
        request_params["stream"] = True
        response = sync_client.messages.create(**request_params)

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
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: AnthropicChatModelType,
    ) -> AsyncGenerator[Reply, None]:

        async_client = AsyncAnthropic(api_key=self.api_key)
        request_params = self._make_request_params(
            input_context=input_context, human_message=human_message, messages=messages, model=model
        )
        request_params["stream"] = True
        response = await async_client.messages.create(**request_params)

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
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[AnthropicChatModelType] = None,
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
        model: Optional[AnthropicChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        stream: bool = False,
        raise_errors: bool = False,
        use_history: bool = True,
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
