import abc
import asyncio
import logging
from dataclasses import dataclass
from inspect import signature
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Optional, Union, cast

from asgiref.sync import async_to_sync
from django.core.checks import Error
from django.core.files import File
from django.template import Context, Template, TemplateDoesNotExist
from django.template.loader import get_template

from .settings import llm_settings
from .types import (
    ChainReply,
    Embed,
    EmbedList,
    LLMChatModelType,
    LLMEmbeddingModelType,
    Message,
    Reply,
)

logger = logging.getLogger(__name__)


class TemplateDict(dict):
    """템플릿 변수 중 존재하지 않는 키는 원래 형태({key})로 유지하는 딕셔너리"""

    def __missing__(self, key):
        return "{" + key + "}"


@dataclass
class DescribeImageRequest:
    image: Union[str, Path, File]
    image_path: str
    system_prompt: Union[str, Template]
    user_prompt: Union[str, Template]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    prompt_context: Optional[dict[str, Any]] = None


class BaseLLM(abc.ABC):
    EMBEDDING_DIMENSIONS = {}

    def __init__(
        self,
        model: LLMChatModelType = "gpt-4o-mini",
        embedding_model: LLMEmbeddingModelType = "text-embedding-3-small",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[Union[str, Template]] = None,
        prompt: Optional[Union[str, Template]] = None,
        output_key: str = "text",
        initial_messages: Optional[list[Message]] = None,
        api_key: Optional[str] = None,
        tools: Optional[list] = None,
    ):
        self.model = model
        self.embedding_model = embedding_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.prompt = prompt
        self.output_key = output_key
        self.history = initial_messages or []
        self.api_key = api_key

        # 기본 도구 설정
        self.default_tools = []
        if tools:
            # tools 모듈을 동적 import (순환 import 방지)
            from .tools import ToolAdapter

            self.default_tools = ToolAdapter.adapt_tools(tools)

    def check(self) -> list[Error]:
        return []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model}, embedding_model={self.embedding_model}, temperature={self.temperature}, max_tokens={self.max_tokens})"

    def __len__(self) -> int:
        return len(self.history)

    def __or__(self, next_llm: Union["BaseLLM", "SequentialChain"]) -> "SequentialChain":
        if isinstance(next_llm, BaseLLM):
            return SequentialChain(self, next_llm)
        elif isinstance(next_llm, SequentialChain):
            next_llm.insert_first(self)
            return next_llm
        else:
            raise TypeError("next_llm must be an instance of BaseLLM or SequentialChain")

    def __ror__(self, prev_llm: Union["BaseLLM", "SequentialChain"]) -> "SequentialChain":
        if isinstance(prev_llm, BaseLLM):
            return SequentialChain(prev_llm, self)
        elif isinstance(prev_llm, SequentialChain):
            prev_llm.append(self)
            return prev_llm
        else:
            raise TypeError("prev_llm must be an instance of BaseLLM or SequentialChain")

    def clear(self):
        """Clear the chat history"""
        self.history = []

    def _process_template(self, template: Union[str, Template], context: dict[str, Any]) -> Optional[str]:
        """템플릿 처리를 위한 공통 메서드"""
        # Django Template 객체인 경우
        if hasattr(template, "render"):
            logger.debug("using template render : %s", template)
            return template.render(Context(context))

        # 문자열인 경우
        elif isinstance(template, str):
            # 파일 기반 템플릿 처리
            if "prompts/" in template and template.endswith((".txt", ".md", ".yaml")):
                try:
                    template_obj = get_template(template)
                    logger.debug("using template render : %s", template)
                    return template_obj.render(context)
                except TemplateDoesNotExist:
                    logger.debug("Template '%s' does not exist", template)
                    return None
            # 장고 템플릿 문법의 문자열
            elif "{{" in template or "{%" in template:
                logger.debug("using string template render : %s ...", repr(template))
                return Template(template).render(Context(context))
            # 일반 문자열 포맷팅 - 존재하는 키만 치환하고 나머지는 그대로 유지
            if context:
                try:
                    return template.format_map(TemplateDict(context))
                except Exception as e:
                    logger.debug("Template formatting failed: %s", e)
                    return template
            return template

        return None

    def get_system_prompt(self, input_context: dict[str, Any], default: Any = None) -> Optional[str]:
        if not self.system_prompt:
            return default

        return self._process_template(self.system_prompt, input_context)

    def get_human_prompt(self, input: Union[str, dict[str, Any]], context: dict[str, Any]) -> str:
        if isinstance(input, (str, Template)) or hasattr(input, "render"):
            result = self._process_template(input, context)
            if result is not None:
                return result

        elif isinstance(input, dict):
            if self.prompt:
                # prompt가 있으면 템플릿 렌더링
                result = self._process_template(self.prompt, context)
                if result is not None:
                    return result
            else:
                # prompt가 없으면 dict를 자동으로 포맷팅
                # context에서 'user_message' 키가 있으면 그것을 사용
                if "user_message" in context:
                    return str(context["user_message"])
                # 아니면 dict의 내용을 읽기 쉬운 형태로 변환
                formatted_parts = []
                for key, value in context.items():
                    if key not in ["choices", "choices_formatted", "choices_optional", "original_choices"]:
                        formatted_parts.append(f"{key}: {value}")
                return "\n".join(formatted_parts) if formatted_parts else ""

        raise ValueError(f"input must be a str, Template, or dict, but got {type(input)}")

    def _update_history(
        self,
        human_message: Message,
        ai_message: Union[str, Message],
    ) -> None:
        if isinstance(ai_message, str):
            ai_message = Message(role="assistant", content=ai_message)

        self.history.extend(
            [
                human_message,
                ai_message,
            ]
        )

    def get_output_key(self) -> str:
        return self.output_key

    def _process_choice_response(
        self, text: str, choices: list[str], choices_optional: bool
    ) -> tuple[Optional[str], Optional[int], float]:
        """
        응답 텍스트에서 choice를 추출하고 검증

        Returns:
            (choice, index, confidence) 튜플
        """
        # JSON 응답 파싱 시도 (OpenAI, Google 등)
        try:
            import json

            data = json.loads(text)
            if isinstance(data, dict) and "choice" in data:
                choice = data["choice"]
                if choice in choices:
                    return choice, choices.index(choice), data.get("confidence", 1.0)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        # 텍스트 매칭
        text_clean = text.strip()

        # 정확한 매칭
        if text_clean in choices:
            return text_clean, choices.index(text_clean), 1.0

        # 대소문자 무시 매칭
        text_lower = text_clean.lower()
        for i, choice in enumerate(choices):
            if choice.lower() == text_lower:
                return choice, i, 0.9

        # 부분 매칭
        for i, choice in enumerate(choices):
            if choice in text_clean or text_clean in choice:
                logger.warning("Partial match found. Response: '%s', Matched: '%s'", text_clean, choice)
                return choice, i, 0.7

        # choices_optional이 True이고 "None of the above"가 포함된 경우
        if choices_optional and ("none of the above" in text_lower or "해당 없음" in text_clean):
            return None, None, 0.8

        # 매칭 실패
        logger.warning("No valid choice found in response: %s", text_clean)
        return None, None, 0.0

    @abc.abstractmethod
    def _make_request_params(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: LLMChatModelType,
    ) -> dict:
        pass

    @abc.abstractmethod
    def _make_ask(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: LLMChatModelType,
    ) -> Reply:
        """Generate a response using the specific LLM provider"""
        pass

    @abc.abstractmethod
    async def _make_ask_async(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: LLMChatModelType,
    ) -> Reply:
        """Generate a response asynchronously using the specific LLM provider"""
        pass

    @abc.abstractmethod
    def _make_ask_stream(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: LLMChatModelType,
    ) -> Generator[Reply, None, None]:
        """Generate a streaming response using the specific LLM provider"""
        yield Reply(text="")

    @abc.abstractmethod
    async def _make_ask_stream_async(
        self,
        input_context: dict[str, Any],
        human_message: Message,
        messages: list[Message],
        model: LLMChatModelType,
    ) -> AsyncGenerator[Reply, None]:
        """Generate a streaming response asynchronously using the specific LLM provider"""
        yield Reply(text="")

    def _ask_impl(
        self,
        input: Union[str, dict[str, str]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[LLMChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        choices: Optional[list[str]] = None,
        choices_optional: bool = False,
        is_async: bool = False,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
        enable_cache: bool = False,
    ):
        """동기 또는 비동기 응답을 생성하는 내부 메서드 (일반/스트리밍)"""
        current_messages = [*self.history] if use_history else []
        current_model: LLMChatModelType = cast(LLMChatModelType, model or self.model)

        if isinstance(input, dict):
            input_context = input
        else:
            input_context = {}

        if context:
            input_context.update(context)

        # enable_cache를 context에 추가
        input_context["enable_cache"] = enable_cache

        # choices 처리
        if choices:
            if len(choices) < 2:
                raise ValueError("choices must contain at least 2 items")

            # choices_optional이 True면 None 옵션 추가
            internal_choices = choices.copy()
            if choices_optional:
                internal_choices.append("None of the above")

            # choices 관련 컨텍스트 추가
            input_context["choices"] = internal_choices
            input_context["choices_formatted"] = "\n".join([f"{i+1}. {c}" for i, c in enumerate(internal_choices)])
            input_context["choices_optional"] = choices_optional
            input_context["original_choices"] = choices

        human_prompt = self.get_human_prompt(input, input_context)
        human_message = Message(role="user", content=human_prompt, files=files)

        # 스트리밍 응답 처리
        if stream:

            async def async_stream_handler() -> AsyncGenerator[Reply, None]:
                try:
                    text_list = []
                    async for ask in self._make_ask_stream_async(
                        input_context=input_context,
                        human_message=human_message,
                        messages=current_messages,
                        model=current_model,
                    ):
                        text_list.append(ask.text)
                        yield ask

                    # 스트리밍 완료 후 choices 처리
                    if choices and text_list:
                        full_text = "".join(text_list)
                        choice, index, confidence = self._process_choice_response(
                            full_text, input_context["original_choices"], choices_optional
                        )
                        # 마지막에 choice 정보를 포함한 Reply 전송
                        yield Reply(text="", choice=choice, choice_index=index, confidence=confidence)

                    if use_history:
                        ai_text = "".join(text_list)
                        self._update_history(human_message=human_message, ai_message=ai_text)
                except Exception as e:
                    if raise_errors:
                        raise e
                    yield Reply(text=f"Error: {str(e)}")

            def sync_stream_handler() -> Generator[Reply, None, None]:
                try:
                    text_list = []
                    for ask in self._make_ask_stream(
                        input_context=input_context,
                        human_message=human_message,
                        messages=current_messages,
                        model=current_model,
                    ):
                        text_list.append(ask.text)
                        yield ask

                    # 스트리밍 완료 후 choices 처리
                    if choices and text_list:
                        full_text = "".join(text_list)
                        choice, index, confidence = self._process_choice_response(
                            full_text, input_context["original_choices"], choices_optional
                        )
                        # 마지막에 choice 정보를 포함한 Reply 전송
                        yield Reply(text="", choice=choice, choice_index=index, confidence=confidence)

                    if use_history:
                        ai_text = "".join(text_list)
                        self._update_history(human_message=human_message, ai_message=ai_text)
                except Exception as e:
                    if raise_errors:
                        raise e
                    yield Reply(text=f"Error: {str(e)}")

            return async_stream_handler() if is_async else sync_stream_handler()

        # 일반 응답 처리
        else:

            async def async_handler() -> Reply:
                try:
                    ask = await self._make_ask_async(
                        input_context=input_context,
                        human_message=human_message,
                        messages=current_messages,
                        model=current_model,
                    )
                except Exception as e:
                    if raise_errors:
                        raise e
                    return Reply(text=f"Error: {str(e)}")
                else:
                    # choices가 있으면 처리
                    if choices:
                        choice, index, confidence = self._process_choice_response(
                            ask.text, input_context["original_choices"], choices_optional
                        )
                        ask.choice = choice
                        ask.choice_index = index
                        ask.confidence = confidence

                    if use_history:
                        self._update_history(human_message=human_message, ai_message=ask.text)
                    return ask

            def sync_handler() -> Reply:
                try:
                    ask = self._make_ask(
                        input_context=input_context,
                        human_message=human_message,
                        messages=current_messages,
                        model=current_model,
                    )
                except Exception as e:
                    if raise_errors:
                        raise e
                    return Reply(text=f"Error: {str(e)}")
                else:
                    # choices가 있으면 처리
                    if choices:
                        choice, index, confidence = self._process_choice_response(
                            ask.text, input_context["original_choices"], choices_optional
                        )
                        ask.choice = choice
                        ask.choice_index = index
                        ask.confidence = confidence

                    if use_history:
                        self._update_history(human_message=human_message, ai_message=ask.text)
                    return ask

            return async_handler() if is_async else sync_handler()

    def invoke(
        self,
        input: Union[str, dict[str, str]],
        files: Optional[list[Union[str, Path, File]]] = None,
        stream: bool = False,
        raise_errors: bool = False,
    ) -> Reply:
        """langchain 호환 메서드: 동기적으로 LLM에 메시지를 전송하고 응답을 반환합니다."""
        return self.ask(input=input, files=files, stream=stream, raise_errors=raise_errors)

    def stream(
        self,
        input: Union[str, dict[str, str]],
        files: Optional[list[Union[str, Path, File]]] = None,
        raise_errors: bool = False,
    ) -> Generator[Reply, None, None]:
        """langchain 호환 메서드: 동기적으로 LLM에 메시지를 전송하고 응답을 스트리밍합니다."""
        return self.ask(input=input, files=files, stream=True, raise_errors=raise_errors)

    def ask(
        self,
        input: Union[str, dict[str, Any]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[LLMChatModelType] = None,
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
        # 기본 도구와 ask 도구를 합침
        merged_tools = self._merge_tools(tools)

        # 도구가 있으면 도구와 함께 처리
        if merged_tools:
            return self._ask_with_tools(
                input=input,
                files=files,
                model=model,
                context=context,
                tools=merged_tools,
                tool_choice=tool_choice,
                max_tool_calls=max_tool_calls,
                choices=choices,
                choices_optional=choices_optional,
                stream=stream,
                use_history=use_history,
                raise_errors=raise_errors,
                enable_cache=enable_cache,
                is_async=False,
            )
        else:
            return self._ask_impl(
                input=input,
                files=files,
                model=model,
                context=context,
                choices=choices,
                choices_optional=choices_optional,
                is_async=False,
                stream=stream,
                use_history=use_history,
                raise_errors=raise_errors,
                enable_cache=enable_cache,
            )

    async def ask_async(
        self,
        input: Union[str, dict[str, Any]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[LLMChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        choices: Optional[list[str]] = None,
        choices_optional: bool = False,
        stream: bool = False,
        raise_errors: bool = False,
        use_history: bool = True,
        enable_cache: bool = False,
        tools: Optional[list] = None,
        tool_choice: str = "auto",
        max_tool_calls: int = 5,
    ) -> Union[Reply, AsyncGenerator[Reply, None]]:
        # 기본 도구와 ask 도구를 합침
        merged_tools = self._merge_tools(tools)

        # 도구가 있으면 도구와 함께 처리
        if merged_tools:
            return_value = self._ask_with_tools(
                input=input,
                files=files,
                model=model,
                context=context,
                tools=merged_tools,
                tool_choice=tool_choice,
                max_tool_calls=max_tool_calls,
                choices=choices,
                choices_optional=choices_optional,
                stream=stream,
                use_history=use_history,
                raise_errors=raise_errors,
                enable_cache=enable_cache,
                is_async=True,
            )
        else:
            return_value = self._ask_impl(
                input=input,
                files=files,
                model=model,
                context=context,
                choices=choices,
                choices_optional=choices_optional,
                is_async=True,
                stream=stream,
                use_history=use_history,
                raise_errors=raise_errors,
                enable_cache=enable_cache,
            )

        if stream:
            return return_value
        return await return_value

    #
    # Function Calling & Tool Support
    #

    def _merge_tools(self, ask_tools: Optional[list]) -> list:
        """기본 도구와 ask 시 제공된 도구를 합칩니다.

        Args:
            ask_tools: ask 호출 시 제공된 도구들

        Returns:
            합쳐진 도구 리스트 (중복시 ask_tools가 우선)
        """
        # tools 모듈을 동적 import (순환 import 방지)
        from .tools import ToolAdapter

        # 1. 기본 tools로 시작 (name을 키로 하는 딕셔너리)
        merged = {tool.name: tool for tool in self.default_tools}

        # 2. ask tools 추가 (중복시 덮어씀)
        if ask_tools:
            adapted_ask_tools = ToolAdapter.adapt_tools(ask_tools)
            for tool in adapted_ask_tools:
                merged[tool.name] = tool

        return list(merged.values())

    def _ask_with_tools(
        self,
        input: Union[str, dict[str, Any]],
        files: Optional[list[Union[str, Path, File]]] = None,
        model: Optional[LLMChatModelType] = None,
        context: Optional[dict[str, Any]] = None,
        tools: Optional[list] = None,
        tool_choice: str = "auto",
        max_tool_calls: int = 5,
        choices: Optional[list[str]] = None,
        choices_optional: bool = False,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
        enable_cache: bool = False,
        is_async: bool = False,
    ):
        """도구와 함께 LLM 호출을 처리합니다.

        Args:
            tools: 이미 Tool 객체로 변환된 도구들의 리스트
        """
        # tools 모듈을 동적 import (순환 import 방지)
        from .tools import ToolExecutor

        # tools는 이미 _merge_tools에서 Tool 객체로 변환됨
        adapted_tools = tools

        # 도구 실행기 준비
        executor = ToolExecutor(adapted_tools)

        # Provider별 도구 스키마 변환 (하위 클래스에서 구현)
        provider_tools = self._convert_tools_for_provider(adapted_tools)

        if is_async:
            return self._ask_with_tools_async(
                input,
                files,
                model,
                context,
                adapted_tools,
                provider_tools,
                executor,
                tool_choice,
                max_tool_calls,
                choices,
                choices_optional,
                stream,
                use_history,
                raise_errors,
                enable_cache,
            )
        else:
            return self._ask_with_tools_sync(
                input,
                files,
                model,
                context,
                adapted_tools,
                provider_tools,
                executor,
                tool_choice,
                max_tool_calls,
                choices,
                choices_optional,
                stream,
                use_history,
                raise_errors,
                enable_cache,
            )

    def _ask_with_tools_sync(
        self,
        input,
        files,
        model,
        context,
        adapted_tools,
        provider_tools,
        executor,
        tool_choice,
        max_tool_calls,
        choices,
        choices_optional,
        stream,
        use_history,
        raise_errors,
        enable_cache,
    ):
        """동기 버전의 도구 호출 처리"""
        # Trace 시작
        if llm_settings.trace_function_calls:
            print("🔍 [TRACE] Function Calling 시작")
            print(f"   입력: {input}")
            print(f"   사용 가능한 도구: {[tool.name for tool in adapted_tools]}")
            print(f"   최대 호출 횟수: {max_tool_calls}")

        # 초기 메시지 준비
        current_messages = [*self.history] if use_history else []
        human_prompt = self.get_human_prompt(input, context or {})

        # 도구 호출 반복
        for call_count in range(max_tool_calls):
            try:
                if llm_settings.trace_function_calls:
                    print(f"\n📞 [TRACE] LLM 호출 #{call_count + 1}")

                # LLM 호출 (도구 포함)
                response = self._make_ask_with_tools_sync(
                    human_prompt if call_count == 0 else None,
                    current_messages,
                    provider_tools,
                    tool_choice,
                    model,
                    files if call_count == 0 else None,
                    enable_cache,
                )

                # 도구 호출 추출
                tool_calls = self._extract_tool_calls_from_response(response)

                if llm_settings.trace_function_calls:
                    if tool_calls:
                        print(f"   LLM이 요청한 도구 호출: {len(tool_calls)}개")
                        for i, call in enumerate(tool_calls):
                            print(f"     {i+1}. {call['name']}({call['arguments']})")
                    else:
                        print(f"   도구 호출 없음, 최종 응답: {response.text[:100]}...")

                # 도구 호출이 없으면 완료
                if not tool_calls:
                    if llm_settings.trace_function_calls:
                        print(f"✅ [TRACE] Function Calling 완료 (총 {call_count + 1}회 호출)")
                    if use_history and call_count == 0:
                        human_message = Message(role="user", content=human_prompt, files=files)
                        self._update_history(human_message, response.text)
                    return response

                # 도구 실행
                if llm_settings.trace_function_calls:
                    print("\n🛠️  [TRACE] 도구 실행 중...")

                for tool_call in tool_calls:
                    try:
                        if llm_settings.trace_function_calls:
                            # 인자를 더 읽기 쉽게 포맷팅
                            args_str = ", ".join([f"{k}={v}" for k, v in tool_call["arguments"].items()])
                            print(f"   실행: {tool_call['name']}({args_str})")

                        result = executor.execute_tool(tool_call["name"], tool_call["arguments"])

                        if llm_settings.trace_function_calls:
                            print(f"   결과: {result}")

                        # 도구 결과를 메시지에 추가
                        current_messages.append(Message(role="assistant", content=f"[Tool Call: {tool_call['name']}]"))
                        current_messages.append(Message(role="user", content=f"[Tool Result: {result}]"))
                    except Exception as e:
                        if llm_settings.trace_function_calls:
                            print(f"   ❌ 오류: {str(e)}")
                        if raise_errors:
                            raise e
                        error_msg = f"Tool execution error: {str(e)}"
                        current_messages.append(Message(role="user", content=f"[Tool Error: {error_msg}]"))

                # 첫 번째 호출이면 히스토리에 추가
                if use_history and call_count == 0:
                    human_message = Message(role="user", content=human_prompt, files=files)
                    current_messages.insert(0, human_message)

            except Exception as e:
                if raise_errors:
                    raise e
                return Reply(text=f"Error in tool processing: {str(e)}")

        # 최대 호출 횟수에 도달한 경우 최종 응답
        try:
            # 마지막 메시지를 human_message로 사용
            if current_messages:
                final_human_message = current_messages[-1]
                final_messages = current_messages[:-1]
            else:
                final_human_message = Message(role="user", content="", files=files)
                final_messages = []

            final_response = self._make_ask(
                input_context={"enable_cache": enable_cache},
                human_message=final_human_message,
                messages=final_messages,
                model=model,
            )
            return final_response
        except Exception as e:
            if raise_errors:
                raise e
            return Reply(text=f"Final response error: {str(e)}")

    async def _ask_with_tools_async(
        self,
        input,
        files,
        model,
        context,
        adapted_tools,
        provider_tools,
        executor,
        tool_choice,
        max_tool_calls,
        choices,
        choices_optional,
        stream,
        use_history,
        raise_errors,
        enable_cache,
    ):
        """비동기 버전의 도구 호출 처리"""
        # 초기 메시지 준비
        current_messages = [*self.history] if use_history else []
        human_prompt = self.get_human_prompt(input, context or {})

        # 도구 호출 반복
        for call_count in range(max_tool_calls):
            try:
                # LLM 호출 (도구 포함)
                response = await self._make_ask_with_tools_async(
                    human_prompt if call_count == 0 else None,
                    current_messages,
                    provider_tools,
                    tool_choice,
                    model,
                    files if call_count == 0 else None,
                    enable_cache,
                )

                # 도구 호출 추출
                tool_calls = self._extract_tool_calls_from_response(response)

                # 도구 호출이 없으면 완료
                if not tool_calls:
                    if use_history and call_count == 0:
                        human_message = Message(role="user", content=human_prompt, files=files)
                        self._update_history(human_message, response.text)
                    return response

                # 도구 실행
                for tool_call in tool_calls:
                    try:
                        result = await executor.execute_tool_async(tool_call["name"], tool_call["arguments"])
                        # 도구 결과를 메시지에 추가
                        current_messages.append(Message(role="assistant", content=f"[Tool Call: {tool_call['name']}]"))
                        current_messages.append(Message(role="user", content=f"[Tool Result: {result}]"))
                    except Exception as e:
                        if raise_errors:
                            raise e
                        error_msg = f"Tool execution error: {str(e)}"
                        current_messages.append(Message(role="user", content=f"[Tool Error: {error_msg}]"))

                # 첫 번째 호출이면 히스토리에 추가
                if use_history and call_count == 0:
                    human_message = Message(role="user", content=human_prompt, files=files)
                    current_messages.insert(0, human_message)

            except Exception as e:
                if raise_errors:
                    raise e
                return Reply(text=f"Error in tool processing: {str(e)}")

        # 최대 호출 횟수에 도달한 경우 최종 응답
        try:
            # 마지막 메시지를 human_message로 사용
            if current_messages:
                final_human_message = current_messages[-1]
                final_messages = current_messages[:-1]
            else:
                final_human_message = Message(role="user", content="", files=files)
                final_messages = []

            final_response = await self._make_ask_async(
                input_context={"enable_cache": enable_cache},
                human_message=final_human_message,
                messages=final_messages,
                model=model,
            )
            return final_response
        except Exception as e:
            if raise_errors:
                raise e
            return Reply(text=f"Final response error: {str(e)}")

    def _convert_tools_for_provider(self, tools):
        """Provider별 도구 스키마 변환 (하위 클래스에서 구현)"""
        # 기본적으로 빈 리스트 반환 (Function Calling 미지원)
        return []

    def _extract_tool_calls_from_response(self, response):
        """응답에서 도구 호출 정보 추출 (하위 클래스에서 구현)"""
        # 기본적으로 빈 리스트 반환
        return []

    def _make_ask_with_tools_sync(self, human_prompt, messages, tools, tool_choice, model, files, enable_cache):
        """도구와 함께 동기 LLM 호출 (하위 클래스에서 구현)"""
        # 기본적으로 일반 ask 호출
        return self._make_ask(
            input_context={},
            human_message=Message(role="user", content=human_prompt or ""),
            messages=messages,
            model=model,
        )

    async def _make_ask_with_tools_async(self, human_prompt, messages, tools, tool_choice, model, files, enable_cache):
        """도구와 함께 비동기 LLM 호출 (하위 클래스에서 구현)"""
        # 기본적으로 일반 ask 호출
        return await self._make_ask_async(
            input_context={},
            human_message=Message(role="user", content=human_prompt or ""),
            messages=messages,
            model=model,
        )

    #
    # embed
    #
    def get_embed_size(self, model: Optional[LLMEmbeddingModelType] = None) -> int:
        return self.EMBEDDING_DIMENSIONS[model or self.embedding_model]

    @property
    def embed_size(self) -> int:
        return self.get_embed_size()

    @abc.abstractmethod
    def embed(
        self,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModelType] = None,
    ) -> Union[Embed, EmbedList]:
        pass

    @abc.abstractmethod
    async def embed_async(
        self,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModelType] = None,
    ) -> Union[Embed, EmbedList]:
        pass

    #
    # describe images / tables
    #

    def describe_images(
        self,
        request: Union[DescribeImageRequest, list[DescribeImageRequest]],
        max_parallel_size: int = 4,
        raise_errors: bool = False,
        enable_cache: bool = False,
    ) -> Reply:
        return async_to_sync(self.describe_images_async)(request, max_parallel_size, raise_errors, enable_cache)

    async def describe_images_async(
        self,
        request: Union[DescribeImageRequest, list[DescribeImageRequest]],
        max_parallel_size: int = 4,
        raise_errors: bool = False,
        enable_cache: bool = False,
    ) -> Union[Reply, list[Reply]]:

        # 최대 4개의 병렬 처리를 위한 세마포어 설정
        semaphore = asyncio.Semaphore(max_parallel_size)

        cls = self.__class__
        sig = signature(cls.__init__)
        is_supported_max_tokens = "max_tokens" in sig.parameters  # max_tokens is not supported in ollama

        if not isinstance(request, (list, tuple)):
            request_list = [request]
        else:
            request_list = request

        async def process_single_image(
            task_request: DescribeImageRequest,
            idx: int,
            total: int,
        ) -> Reply:
            logger.info("request describe_images [%d/%d] : %s", idx + 1, total, task_request.image_path)

            if is_supported_max_tokens:
                llm = cls(
                    model=self.model,
                    temperature=self.temperature if task_request.temperature is None else task_request.temperature,
                    max_tokens=self.max_tokens if task_request.max_tokens is None else task_request.max_tokens,
                    system_prompt=task_request.system_prompt,
                )
            else:
                llm = cls(
                    model=self.model,
                    temperature=self.temperature if task_request.temperature is None else task_request.temperature,
                    system_prompt=task_request.system_prompt,
                )
                if task_request.max_tokens is not None:
                    logger.debug("max_tokens is not supported for %s LLM", self.model)

            reply = await llm.ask_async(
                input=task_request.user_prompt,
                files=[task_request.image],
                context=task_request.prompt_context,
                raise_errors=raise_errors,
                enable_cache=enable_cache,
            )
            logger.debug("image description for %s : %s", task_request.image_path, repr(reply.text))
            return reply

        async def process_with_semaphore(request_item, idx, total):
            async with semaphore:
                return await process_single_image(request_item, idx, total)

        # 세마포어를 통해 병렬 처리 제한
        tasks = [process_with_semaphore(request, idx, len(request_list)) for idx, request in enumerate(request_list)]
        reply_list = await asyncio.gather(*tasks)

        assert len(request_list) == len(reply_list)

        for _request in request_list:
            if hasattr(_request.image, "seek"):
                _request.image.seek(0)

        if isinstance(request, (list, tuple)):
            return reply_list

        return reply_list[0]


class SequentialChain:
    def __init__(self, *args):
        self.llms: list[BaseLLM] = list(args)

    def insert_first(self, llm) -> "SequentialChain":
        self.llms.insert(0, llm)
        return self

    def append(self, llm) -> "SequentialChain":
        self.llms.append(llm)
        return self

    def ask(self, inputs: dict[str, Any]) -> ChainReply:
        """체인의 각 LLM을 순차적으로 실행합니다. 이전 LLM의 출력이 다음 LLM의 입력으로 전달됩니다."""

        for llm in self.llms:
            if llm.prompt is None:
                raise ValueError(f"prompt is required for LLM: {llm}")

        known_values = inputs.copy()
        reply_list = []
        for llm in self.llms:
            reply = llm.ask(known_values)
            reply_list.append(reply)

            output_key = llm.get_output_key()
            known_values[output_key] = str(reply)

        return ChainReply(
            values=known_values,
            reply_list=reply_list,
        )
