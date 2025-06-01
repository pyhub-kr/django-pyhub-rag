import logging
import re
from base64 import b64decode
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Optional, Union, cast

import pydantic
from django.core.checks import Error
from django.core.files import File
from django.template import Template
from google import genai
from google.genai.types import (
    Content,
    EmbedContentResponse,
    GenerateContentConfig,
    GenerateContentResponse,
    Part,
)

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
    GoogleChatModelType,
    GoogleEmbeddingModelType,
    Message,
    Reply,
    Usage,
)
from .utils.files import FileType, encode_files

logger = logging.getLogger(__name__)


class GoogleLLM(BaseLLM):
    EMBEDDING_DIMENSIONS = {
        "text-embedding-004": 768,
    }

    def __init__(
        self,
        model: GoogleChatModelType = "gemini-2.0-flash",
        embedding_model: GoogleEmbeddingModelType = "text-embedding-004",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[Union[str, Template]] = None,
        prompt: Optional[Union[str, Template]] = None,
        output_key: str = "text",
        initial_messages: Optional[list[Message]] = None,
        api_key: Optional[str] = None,
        tools: Optional[list] = None,
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
            api_key=api_key or rag_settings.google_api_key,
            tools=tools,
        )

    def check(self) -> list[Error]:
        errors = super().check()

        if not self.api_key:
            errors.append(
                Error(
                    "Google API key is not set or is invalid.",
                    hint="Please check your Google API key.",
                    obj=self,
                )
            )

        return errors

    def _make_request_params(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: GoogleChatModelType,
    ) -> dict:
        contents: list[Content] = [
            Content(
                role="user" if message.role == "user" else "model",
                parts=[Part(text=message.content)],
            )
            for message in messages
        ]

        # https://docs.anthropic.com/en/docs/build-with-claude/vision
        image_urls = encode_files(
            human_message.files,
            allowed_types=FileType.IMAGE,
            convert_mode="base64",
        )

        image_parts: list[Part] = []
        if image_urls:
            base64_url_pattern = r"^data:([^;]+);base64,(.+)"

            for image_url in image_urls:
                base64_url_match = re.match(base64_url_pattern, image_url)
                if base64_url_match:
                    mimetype = base64_url_match.group(1)
                    b64_str = base64_url_match.group(2)
                    image_data = b64decode(b64_str)
                    image_part = Part.from_bytes(data=image_data, mime_type=mimetype)
                    image_parts.append(image_part)
                else:
                    raise ValueError(
                        f"Invalid image data: {image_url}. Google Gemini API only supports base64 encoded images."
                    )

        contents.append(
            Content(
                role="user" if human_message.role == "user" else "model",
                parts=[
                    *image_parts,
                    Part(text=human_message.content),
                ],
            )
        )

        system_prompt: Optional[str] = self.get_system_prompt(input_context)
        if system_prompt is None:
            system_instruction = None
        else:
            system_instruction = Content(parts=[Part(text=system_prompt)])

        config = GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=self.max_tokens,
            temperature=self.temperature,
        )

        return dict(
            model=model,
            contents=contents,
            config=config,
        )

    def _make_ask(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: GoogleChatModelType,
    ) -> Reply:
        client = genai.Client(api_key=self.api_key)
        request_params = self._make_request_params(input_context, human_message, messages, model)

        cache_key, cached_value = cache_make_key_and_get(
            "google",
            request_params,
            cache_alias="google",
            enable_cache=input_context.get("enable_cache", False),
        )

        response: Optional[GenerateContentResponse] = None
        is_cached = False
        if cached_value is not None:
            try:
                response = GenerateContentResponse.model_validate_json(cached_value)
                is_cached = True
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            logger.debug("request to google genai")
            response = client.models.generate_content(**request_params)
            if cache_key is not None:
                cache_set(cache_key, response.model_dump_json(), alias="google")

        assert response is not None

        # 캐시된 응답인 경우 usage를 0으로 설정
        usage_input = 0 if is_cached else (response.usage_metadata.prompt_token_count or 0)
        usage_output = 0 if is_cached else (response.usage_metadata.candidates_token_count or 0)

        return Reply(
            text=response.text,
            usage=Usage(
                input=usage_input,
                output=usage_output,
            ),
        )

    async def _make_ask_async(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: GoogleChatModelType,
    ) -> Reply:
        client = genai.Client(api_key=self.api_key)
        request_params = self._make_request_params(input_context, human_message, messages, model)

        cache_key, cached_value = await cache_make_key_and_get_async(
            "google",
            request_params,
            cache_alias="google",
            enable_cache=input_context.get("enable_cache", False),
        )

        response: Optional[GenerateContentResponse] = None
        is_cached = False
        if cached_value is not None:
            try:
                response = GenerateContentResponse.model_validate_json(cached_value)
                is_cached = True
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            logger.debug("request to google genai")
            response = await client.aio.models.generate_content(**request_params)
            if cache_key is not None:
                await cache_set_async(cache_key, response.model_dump_json(), alias="google")

        assert response is not None

        # 캐시된 응답인 경우 usage를 0으로 설정
        usage_input = 0 if is_cached else (response.usage_metadata.prompt_token_count or 0)
        usage_output = 0 if is_cached else (response.usage_metadata.candidates_token_count or 0)

        return Reply(
            text=response.text,
            usage=Usage(
                input=usage_input,
                output=usage_output,
            ),
        )

    def _make_ask_stream(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: GoogleChatModelType,
    ) -> Generator[Reply, None, None]:
        client = genai.Client(api_key=self.api_key)
        request_params = self._make_request_params(input_context, human_message, messages, model)

        cache_key, cached_value = cache_make_key_and_get(
            "google",
            dict(stream=True, **request_params),
            cache_alias="google",
            enable_cache=input_context.get("enable_cache", False),
        )

        if cached_value is not None:
            reply_list = cast(list[Reply], cached_value)
            for reply in reply_list:
                if reply.usage is not None:
                    # 캐시된 응답인 경우 usage를 0으로 설정
                    reply.usage = Usage(input=0, output=0)
                yield reply

        else:
            response = client.models.generate_content_stream(**request_params)

            input_tokens = 0
            output_tokens = 0

            reply_list: list[Reply] = []
            for chunk in response:
                reply = Reply(text=chunk.text)
                reply_list.append(reply)
                yield reply
                input_tokens += chunk.usage_metadata.prompt_token_count or 0
                output_tokens += chunk.usage_metadata.candidates_token_count or 0

            if input_tokens > 0 or output_tokens > 0:
                usage = Usage(input=input_tokens, output=output_tokens)
                reply = Reply(text="", usage=usage)
                reply_list.append(reply)
                yield reply

            if cache_key is not None:
                cache_set(cache_key, reply_list, alias="google")

    async def _make_ask_stream_async(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: GoogleChatModelType,
    ) -> AsyncGenerator[Reply, None]:
        client = genai.Client(api_key=self.api_key)
        request_params = self._make_request_params(input_context, human_message, messages, model)

        cache_key, cached_value = await cache_make_key_and_get_async(
            "google",
            dict(stream=True, **request_params),
            cache_alias="google",
            enable_cache=input_context.get("enable_cache", False),
        )

        if cached_value is not None:
            reply_list = cast(list[Reply], cached_value)
            for reply in reply_list:
                if reply.usage is not None:
                    # 캐시된 응답인 경우 usage를 0으로 설정
                    reply.usage = Usage(input=0, output=0)
                yield reply

        else:
            logger.debug("request to google genai")

            response = await client.aio.models.generate_content_stream(**request_params)

            input_tokens = 0
            output_tokens = 0

            reply_list: list[Reply] = []
            async for chunk in response:
                reply = Reply(text=chunk.text)
                reply_list.append(reply)
                yield reply
                input_tokens += chunk.usage_metadata.prompt_token_count or 0
                output_tokens += chunk.usage_metadata.candidates_token_count or 0

            if input_tokens > 0 or output_tokens > 0:
                usage = Usage(input=input_tokens, output=output_tokens)
                reply = Reply(text="", usage=usage)
                reply_list.append(reply)
                yield reply

            if cache_key is not None:
                await cache_set_async(cache_key, reply_list, alias="google")

    def ask(
        self,
        input: Union[str, dict[str, Any]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[GoogleChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        choices: Optional[list[str]] = None,
        choices_optional: bool = False,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
        enable_cache: bool = False,
        tools: Optional[list] = None,
        tool_choice: str = "auto",
        max_tool_calls: int = 5,
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
            tools=tools,
            tool_choice=tool_choice,
            max_tool_calls=max_tool_calls,
        )

    async def ask_async(
        self,
        input: Union[str, dict[str, Any]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[GoogleChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        choices: Optional[list[str]] = None,
        choices_optional: bool = False,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
        enable_cache: bool = False,
        tools: Optional[list] = None,
        tool_choice: str = "auto",
        max_tool_calls: int = 5,
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
            tools=tools,
            tool_choice=tool_choice,
            max_tool_calls=max_tool_calls,
        )

    def embed(
        self,
        input: Union[str, list[str]],
        model: Optional[GoogleEmbeddingModelType] = None,
        enable_cache: bool = False,
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(GoogleEmbeddingModelType, model or self.embedding_model)

        client = genai.Client(api_key=self.api_key)
        request_params = dict(
            model=str(embedding_model),
            contents=input,
            # config=EmbedContentConfig(output_dimensionality=10),
        )

        cache_key, cached_value = cache_make_key_and_get(
            "google",
            request_params,
            cache_alias="google",
            enable_cache=enable_cache,
        )

        response: Optional[EmbedContentResponse] = None
        is_cached = False
        if cached_value is not None:
            try:
                response = EmbedContentResponse.model_validate_json(cached_value)
                is_cached = True
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            logger.debug("request to google embed")
            response = client.models.embed_content(**request_params)
            if cache_key is not None:
                cache_set(cache_key, response.model_dump_json(), alias="google")

        # TODO: response에 usage_metadata가 없음 - 캐시된 응답인 경우에도 None 유지
        usage = None
        if isinstance(input, str):
            return Embed(response.embeddings[0].values, usage=usage)
        return EmbedList([Embed(v.values) for v in response.embeddings], usage=usage)

    async def embed_async(
        self,
        input: Union[str, list[str]],
        model: Optional[GoogleEmbeddingModelType] = None,
        enable_cache: bool = False,
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(GoogleEmbeddingModelType, model or self.embedding_model)

        client = genai.Client(api_key=self.api_key)
        request_params = dict(
            model=str(embedding_model),
            contents=input,
            # config=EmbedContentConfig(output_dimensionality=10),
        )

        cache_key, cached_value = await cache_make_key_and_get_async(
            "google",
            request_params,
            cache_alias="google",
            enable_cache=enable_cache,
        )

        response: Optional[EmbedContentResponse] = None
        is_cached = False
        if cached_value is not None:
            try:
                response = EmbedContentResponse.model_validate_json(cached_value)
                is_cached = True
            except pydantic.ValidationError as e:
                logger.error("Invalid cached value : %s", e)

        if response is None:
            response = await client.aio.models.embed_content(**request_params)
            if cache_key is not None:
                await cache_set_async(cache_key, response.model_dump_json(), alias="google")

        # TODO: response에 usage_metadata가 없음 - 캐시된 응답인 경우에도 None 유지
        usage = None
        if isinstance(input, str):
            return Embed(response.embeddings[0].values, usage=usage)
        return EmbedList([Embed(v.values) for v in response.embeddings], usage=usage)

    def _convert_tools_for_provider(self, tools):
        """Google Function Calling 형식으로 도구 변환"""
        from .tools import ProviderToolConverter

        return [ProviderToolConverter.to_google_function(tool) for tool in tools]

    def _extract_tool_calls_from_response(self, response):
        """Google 응답에서 function_call 추출"""
        tool_calls = []

        # Response가 Reply 객체인 경우 원본 응답에서 function_call 추출
        if hasattr(response, "_raw_response") and hasattr(response._raw_response, "candidates"):
            candidates = response._raw_response.candidates
            if candidates and len(candidates) > 0:
                candidate = candidates[0]
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                    for part in candidate.content.parts:
                        # function_call 속성이 있고 None이 아닌지 확인
                        if hasattr(part, "function_call") and part.function_call is not None:
                            # function_call 객체에 name과 args 속성이 있는지 확인
                            if hasattr(part.function_call, "name") and hasattr(part.function_call, "args"):
                                tool_calls.append(
                                    {
                                        "id": f"call_{len(tool_calls)}",  # Google doesn't provide call IDs
                                        "name": part.function_call.name,
                                        "arguments": part.function_call.args,
                                    }
                                )
                            else:
                                # function_call 객체에 필요한 속성이 없는 경우 로깅
                                logger.warning(
                                    "function_call object missing required attributes: %s", part.function_call
                                )

        return tool_calls

    def _make_ask_with_tools_sync(self, human_prompt, messages, tools, tool_choice, model, files, enable_cache):
        """Google Function Calling을 사용한 동기 호출"""
        from google.genai.types import FunctionDeclaration, Tool


        # 메시지 준비
        google_messages = []
        for msg in messages:
            google_messages.append(
                Content(role="user" if msg.role == "user" else "model", parts=[Part(text=msg.content)])
            )

        if human_prompt:
            google_messages.append(Content(role="user", parts=[Part(text=human_prompt)]))

        # 도구를 Google Tool 형식으로 변환
        google_tools = []
        if tools:
            function_declarations = []
            for tool in tools:
                function_declarations.append(
                    FunctionDeclaration(
                        name=tool["name"], description=tool["description"], parameters=tool["parameters"]
                    )
                )
            google_tools = [Tool(function_declarations=function_declarations)]

        # Google API 호출
        client = genai.Client(api_key=self.api_key)

        system_prompt = None
        if messages and messages[0].role == "system":
            system_prompt = Content(parts=[Part(text=messages[0].content)])
            google_messages = google_messages[1:]  # 시스템 메시지 제거

        config = GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.max_tokens,
            temperature=self.temperature,
            tools=google_tools if google_tools else None,
        )

        try:
            response = client.models.generate_content(
                model=model or self.model, contents=google_messages, config=config
            )

            # Reply 객체로 변환
            usage = Usage(
                input=response.usage_metadata.prompt_token_count or 0,
                output=response.usage_metadata.candidates_token_count or 0,
            )

            reply = Reply(text=response.text or "", usage=usage)

            # 원본 응답을 저장하여 function_call 추출에 사용
            reply._raw_response = response

            return reply

        except Exception as e:
            logger.error(f"Google API error: {e}")
            return Reply(text=f"API Error: {str(e)}")

    async def _make_ask_with_tools_async(self, human_prompt, messages, tools, tool_choice, model, files, enable_cache):
        """Google Function Calling을 사용한 비동기 호출"""
        from google.genai.types import FunctionDeclaration, Tool


        # 메시지 준비
        google_messages = []
        for msg in messages:
            google_messages.append(
                Content(role="user" if msg.role == "user" else "model", parts=[Part(text=msg.content)])
            )

        if human_prompt:
            google_messages.append(Content(role="user", parts=[Part(text=human_prompt)]))

        # 도구를 Google Tool 형식으로 변환
        google_tools = []
        if tools:
            function_declarations = []
            for tool in tools:
                function_declarations.append(
                    FunctionDeclaration(
                        name=tool["name"], description=tool["description"], parameters=tool["parameters"]
                    )
                )
            google_tools = [Tool(function_declarations=function_declarations)]

        # Google API 호출
        client = genai.Client(api_key=self.api_key)

        system_prompt = None
        if messages and messages[0].role == "system":
            system_prompt = Content(parts=[Part(text=messages[0].content)])
            google_messages = google_messages[1:]  # 시스템 메시지 제거

        config = GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=self.max_tokens,
            temperature=self.temperature,
            tools=google_tools if google_tools else None,
        )

        try:
            response = await client.aio.models.generate_content(
                model=model or self.model, contents=google_messages, config=config
            )

            # Reply 객체로 변환
            usage = Usage(
                input=response.usage_metadata.prompt_token_count or 0,
                output=response.usage_metadata.candidates_token_count or 0,
            )

            reply = Reply(text=response.text or "", usage=usage)

            # 원본 응답을 저장하여 function_call 추출에 사용
            reply._raw_response = response

            return reply

        except Exception as e:
            logger.error(f"Google API error: {e}")
            return Reply(text=f"API Error: {str(e)}")


__all__ = ["GoogleLLM"]
