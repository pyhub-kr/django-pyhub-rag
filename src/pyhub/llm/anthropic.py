import logging
import re
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Optional, Union, cast

import anthropic.types
import pydantic
from anthropic import NOT_GIVEN as ANTHROPIC_NOT_GIVEN
from anthropic import Anthropic as SyncAnthropic
from anthropic import AsyncAnthropic
from django.core.checks import Error
from django.core.files import File
from django.template import Template

from pyhub.caches import (
    cache_make_key_and_get,
    cache_make_key_and_get_async,
    cache_set,
    cache_set_async,
)
from pyhub.rag.settings import rag_settings

from .base import BaseLLM
from .types import AnthropicChatModelType, Embed, EmbedList, Message, Reply, SelectResponse, Usage
from .utils.files import FileType, encode_files

logger = logging.getLogger(__name__)


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

        cache_key, cached_value = cache_make_key_and_get(
            "anthropic",
            request_params,
            cache_alias="anthropic",
        )

        response: Optional[anthropic.types.Message] = None
        if cached_value is not None:
            try:
                response = anthropic.types.Message.model_validate_json(cached_value)
            except pydantic.ValidationError as e:
                logger.error("cached_value is valid : %s", e)

        if response is None:
            logger.debug("request to anthropic")
            response = sync_client.messages.create(**request_params)
            if cache_key is not None:
                cache_set(cache_key, response.model_dump_json(), alias="anthropic")

        assert response is not None

        return Reply(
            text=response.content[0].text,
            usage=Usage(input=response.usage.input_tokens, output=response.usage.output_tokens),
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

        cache_key, cached_value = await cache_make_key_and_get_async(
            "anthropic",
            request_params,
            cache_alias="anthropic",
        )

        response: Optional[anthropic.types.Message] = None
        if cached_value is not None:
            try:
                response = anthropic.types.Message.model_validate_json(cached_value)
            except pydantic.ValidationError as e:
                logger.error("cached_value is valid : %s", e)

        if response is None:
            logger.debug("request to anthropic")
            response = await async_client.messages.create(**request_params)
            if cache_key is not None:
                await cache_set_async(cache_key, response.model_dump_json(), alias="anthropic")

        assert response is not None

        return Reply(
            text=response.content[0].text,
            usage=Usage(input=response.usage.input_tokens, output=response.usage.output_tokens),
        )

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

        cache_key, cached_value = cache_make_key_and_get(
            "anthropic",
            request_params,
            cache_alias="anthropic",
        )

        if cached_value is not None:
            reply_list = cast(list[Reply], cached_value)
            for reply in reply_list:
                reply.usage = None
                yield reply
        else:
            logger.debug("request to anthropic")

            response = sync_client.messages.create(**request_params)

            input_tokens = 0
            output_tokens = 0

            reply_list: list[Reply] = []
            for chunk in response:
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    reply = Reply(text=chunk.delta.text)
                    reply_list.append(reply)
                    yield reply
                elif hasattr(chunk, "type") and chunk.type == "content_block_delta":
                    if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                        reply = Reply(text=chunk.delta.text)
                        reply_list.append(reply)
                        yield reply
                    elif hasattr(chunk, "content_block") and hasattr(chunk.content_block, "text"):
                        reply = Reply(text=chunk.content_block.text)
                        reply_list.append(reply)
                        yield reply

                if hasattr(chunk, "message") and hasattr(chunk.message, "usage"):
                    input_tokens += getattr(chunk.message.usage, "input_tokens", None) or 0
                    output_tokens += getattr(chunk.message.usage, "output_tokens", None) or 0

                if hasattr(chunk, "usage") and chunk.usage:
                    input_tokens += getattr(chunk.usage, "input_tokens", None) or 0
                    output_tokens += getattr(chunk.usage, "output_tokens", None) or 0

            reply = Reply(text="", usage=Usage(input_tokens, output_tokens))
            reply_list.append(reply)
            yield reply

            if cache_key is not None:
                cache_set(cache_key, reply_list, alias="anthropic")

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

        cache_key, cached_value = await cache_make_key_and_get_async(
            "anthropic",
            request_params,
            cache_alias="anthropic",
        )

        if cached_value is not None:
            reply_list = cast(list[Reply], cached_value)
            for reply in reply_list:
                reply.usage = None
                yield reply
        else:
            logger.debug("request to anthropic")
            response = await async_client.messages.create(**request_params)

            input_tokens = 0
            output_tokens = 0

            reply_list: list[Reply] = []
            async for chunk in response:
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    reply = Reply(text=chunk.delta.text)
                    reply_list.append(reply)
                    yield reply
                elif hasattr(chunk, "type") and chunk.type == "content_block_delta":
                    if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                        reply = Reply(text=chunk.delta.text)
                        reply_list.append(reply)
                        yield reply
                    elif hasattr(chunk, "content_block") and hasattr(chunk.content_block, "text"):
                        reply = Reply(text=chunk.content_block.text)
                        reply_list.append(reply)
                        yield reply

                if hasattr(chunk, "message") and hasattr(chunk.message, "usage"):
                    input_tokens += getattr(chunk.message.usage, "input_tokens", None) or 0
                    output_tokens += getattr(chunk.message.usage, "output_tokens", None) or 0

                if hasattr(chunk, "usage") and chunk.usage:
                    input_tokens += getattr(chunk.usage, "input_tokens", None) or 0
                    output_tokens += getattr(chunk.usage, "output_tokens", None) or 0

            reply = Reply(text="", usage=Usage(input_tokens, output_tokens))
            reply_list.append(reply)
            yield reply

            if cache_key is not None:
                await cache_set_async(cache_key, reply_list, alias="anthropic")

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

    def _make_select(
        self,
        context: dict[str, Any],
        choices: list[str],
        model: AnthropicChatModelType,
    ) -> SelectResponse:
        """Anthropic의 프롬프트 엔지니어링을 통한 선택 구현"""
        sync_client = SyncAnthropic(api_key=self.api_key)

        # 강력한 시스템 프롬프트
        allow_none = context.get("allow_none", False)
        system_prompt = """You are a selection assistant. Your task is to choose exactly ONE option from a given list.

CRITICAL RULES:
1. You MUST respond with ONLY the exact text of your chosen option
2. Do NOT add any explanation, punctuation, or additional text
3. Do NOT modify the option text in any way
4. Your entire response should be the chosen option, nothing more

If you add anything other than the exact option text, your response will be considered invalid."""

        if allow_none:
            system_prompt += f"\n\nIMPORTANT: {context.get('instruction_none', '')}"

        # 사용자 프롬프트
        user_context = context.get("user_context", "")
        user_prompt = f"""Choose ONE option from this list:
{context['choices_formatted']}

{f"Context to consider: {user_context}" if user_context else ""}

Remember: Respond with ONLY the exact text of your chosen option."""

        # API 호출
        messages = [{"role": "user", "content": user_prompt}]

        request_params = {
            "model": model,
            "messages": messages,
            "system": system_prompt,
            "temperature": 0.1,  # 일관된 선택을 위해 낮은 temperature
            "max_tokens": 100,
        }

        # 캐시 확인
        cache_key, cached_value = cache_make_key_and_get(
            "anthropic_select",
            request_params,
            cache_alias="anthropic",
        )

        if cached_value is not None:
            return cached_value

        try:
            response = sync_client.messages.create(**request_params)

            # 응답 텍스트 추출 및 정리
            selected_text = response.content[0].text.strip()

            # Usage 정보 추출
            usage = None
            if response.usage:
                usage = Usage(
                    input=response.usage.input_tokens or 0,
                    output=response.usage.output_tokens or 0,
                )

            # 정확한 매칭 시도
            if selected_text in choices:
                select_response = SelectResponse(choice=selected_text, index=choices.index(selected_text), usage=usage)

                # 캐시 저장
                if cache_key is not None:
                    cache_set(cache_key, select_response, alias="anthropic")

                return select_response

            # 부분 매칭 시도 (대소문자 무시)
            selected_lower = selected_text.lower()
            for i, choice in enumerate(choices):
                if choice.lower() == selected_lower:
                    select_response = SelectResponse(choice=choice, index=i, usage=usage)

                    if cache_key is not None:
                        cache_set(cache_key, select_response, alias="anthropic")

                    return select_response

            # 부분 포함 매칭 시도
            for i, choice in enumerate(choices):
                if choice in selected_text or selected_text in choice:
                    logger.warning("Partial match found. Response: '%s', Matched: '%s'", selected_text, choice)
                    select_response = SelectResponse(choice=choice, index=i, usage=usage)

                    if cache_key is not None:
                        cache_set(cache_key, select_response, alias="anthropic")

                    return select_response

            # 매칭 실패
            raise RuntimeError(f"Could not match response '{selected_text}' to any of the choices: {choices}")

        except Exception as e:
            logger.error("Error in Anthropic select: %s", str(e))
            raise

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
