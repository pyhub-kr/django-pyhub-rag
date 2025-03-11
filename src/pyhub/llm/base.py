import abc
import logging
from typing import Any, AsyncGenerator, Generator, Optional, Union, cast

from django.core.checks import Error
from django.template import Context, Template

from .types import (
    ChainReply,
    Embed,
    EmbedList,
    LLMChatModel,
    LLMEmbeddingModel,
    Message,
    Reply,
)

logger = logging.getLogger(__name__)


class BaseLLM(abc.ABC):
    EMBEDDING_DIMENSIONS = {}

    def __init__(
        self,
        model: LLMChatModel = "gpt-4o-mini",
        embedding_model: LLMEmbeddingModel = "text-embedding-3-small",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[Union[str, Template]] = None,
        prompt: Optional[Union[str, Template]] = None,
        output_key: str = "text",
        initial_messages: Optional[list[Message]] = None,
        api_key: Optional[str] = None,
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
            raise TypeError(f"next_llm must be an instance of BaseLLM or SequentialChain")

    def __ror__(self, prev_llm: Union["BaseLLM", "SequentialChain"]) -> "SequentialChain":
        if isinstance(prev_llm, BaseLLM):
            return SequentialChain(prev_llm, self)
        elif isinstance(prev_llm, SequentialChain):
            prev_llm.append(self)
            return prev_llm
        else:
            raise TypeError(f"prev_llm must be an instance of BaseLLM or SequentialChain")

    def clear(self):
        """Clear the chat history"""
        self.history = []

    def get_system_prompt(self, input_context: dict[str, Any], default: Any = None) -> Optional[str]:
        if not self.system_prompt:
            if default is not None:
                return default
            return None

        if hasattr(self.system_prompt, "render"):
            return self.system_prompt.render(Context(input_context))
        return self.system_prompt.format(**input_context)

    def get_human_prompt(self, input: Union[str, dict[str, Any]], context: dict[str, Any]) -> str:
        if isinstance(input, str):
            return input.format(**context)
        elif hasattr(input, "render"):
            return input.render(Context(context))
        elif isinstance(input, dict):
            if not self.prompt:
                raise ValueError("prompt is required when human_message is a dict")

            # Django Template 지원 추가
            if hasattr(self.prompt, "render"):
                human_prompt = self.prompt.render(Context(context))
            else:
                human_prompt = self.prompt.format(**context)
        else:
            raise ValueError(f"input must be a str or a dict, but got {type(input)}")

        return human_prompt

    def get_output_key(self) -> str:
        return self.output_key

    @abc.abstractmethod
    def _make_ask(self, input_context: dict[str, Any], messages: list[Message], model: LLMChatModel) -> Reply:
        """Generate a response using the specific LLM provider"""
        pass

    @abc.abstractmethod
    async def _make_ask_async(
        self, input_context: dict[str, Any], messages: list[Message], model: LLMChatModel
    ) -> Reply:
        """Generate a response asynchronously using the specific LLM provider"""
        pass

    @abc.abstractmethod
    def _make_ask_stream(
        self, input_context: dict[str, Any], messages: list[Message], model: LLMChatModel
    ) -> Generator[Reply, None, None]:
        """Generate a streaming response using the specific LLM provider"""
        yield Reply(text="")

    @abc.abstractmethod
    async def _make_ask_stream_async(
        self, input_context: dict[str, Any], messages: list[Message], model: LLMChatModel
    ) -> AsyncGenerator[Reply, None]:
        """Generate a streaming response asynchronously using the specific LLM provider"""
        yield Reply(text="")

    def _prepare_messages(self, input: str, current_messages: list[Message]) -> list[Message]:
        if input:
            current_messages.append(Message(role="user", content=input))
        return current_messages

    def _update_history(self, human_prompt: str, ai_message: str) -> None:
        if human_prompt is not None:
            self.history.extend(
                [
                    Message(role="user", content=human_prompt),
                    Message(role="assistant", content=ai_message),
                ]
            )

    def _ask_impl(
        self,
        input: Union[str, dict[str, str]],
        model: Optional[LLMChatModel] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        is_async: bool = False,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
    ):
        """동기 또는 비동기 응답을 생성하는 내부 메서드 (일반/스트리밍)"""
        current_messages = [*self.history] if use_history else []
        current_model: LLMChatModel = cast(LLMChatModel, model or self.model)

        if isinstance(input, dict):
            input_context = input
        else:
            input_context = {}

        if context:
            input_context.update(context)

        human_prompt = self.get_human_prompt(input, input_context)
        current_messages = self._prepare_messages(human_prompt, current_messages)

        # 스트리밍 응답 처리
        if stream:

            async def async_stream_handler() -> AsyncGenerator[Reply, None]:
                try:
                    text_list = []
                    async for ask in self._make_ask_stream_async(input_context, current_messages, current_model):
                        text_list.append(ask.text)
                        yield ask

                    if use_history:
                        full_text = "".join(text_list)
                        self._update_history(human_prompt, full_text)
                except Exception as e:
                    if raise_errors:
                        raise e
                    logger.error(f"Error occurred during streaming API call: {str(e)}")
                    yield Reply(text=f"Error occurred during streaming API call: {str(e)}")

            def sync_stream_handler() -> Generator[Reply, None, None]:
                try:
                    text_list = []
                    for ask in self._make_ask_stream(input_context, current_messages, current_model):
                        text_list.append(ask.text)
                        yield ask

                    if use_history:
                        full_text = "".join(text_list)
                        self._update_history(human_prompt, full_text)
                except Exception as e:
                    if raise_errors:
                        raise e
                    logger.error(f"Error occurred during streaming API call: {str(e)}")
                    yield Reply(text=f"Error occurred during streaming API call: {str(e)}")

            return async_stream_handler() if is_async else sync_stream_handler()

        # 일반 응답 처리
        else:

            async def async_handler() -> Reply:
                try:
                    ask = await self._make_ask_async(input_context, current_messages, current_model)
                except Exception as e:
                    if raise_errors:
                        raise e
                    logger.error(f"Error occurred during API call: {str(e)}")
                    return Reply(text=f"Error occurred during API call: {str(e)}")
                else:
                    if use_history:
                        self._update_history(human_prompt, ask.text)
                    return ask

            def sync_handler() -> Reply:
                try:
                    ask = self._make_ask(input_context, current_messages, current_model)
                except Exception as e:
                    if raise_errors:
                        raise e
                    logger.error(f"Error occurred during API call: {str(e)}")
                    return Reply(text=f"Error occurred during API call: {str(e)}")
                else:
                    if use_history:
                        self._update_history(human_prompt, ask.text)
                    return ask

            return async_handler() if is_async else sync_handler()

    def invoke(self, input: Union[str, dict[str, str]], stream: bool = False) -> Reply:
        """langchain 호환 메서드: 동기적으로 LLM에 메시지를 전송하고 응답을 반환합니다."""
        return self.ask(input, stream=stream)

    def stream(self, input: Union[str, dict[str, str]]) -> Generator[Reply, None, None]:
        """langchain 호환 메서드: 동기적으로 LLM에 메시지를 전송하고 응답을 스트리밍합니다."""
        return self.ask(input, stream=True)

    def ask(
        self,
        input: Union[str, dict[str, Any]],
        model: Optional[LLMChatModel] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        stream: bool = False,
        use_history: bool = True,
        raise_errors: bool = False,
    ) -> Union[Reply, Generator[Reply, None, None]]:
        return self._ask_impl(
            input,
            model,
            context,
            is_async=False,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
        )

    async def ask_async(
        self,
        input: Union[str, dict[str, Any]],
        model: Optional[LLMChatModel] = None,
        context: Optional[dict[str, Any]] = None,
        *,
        stream: bool = False,
        raise_errors: bool = False,
        use_history: bool = True,
    ) -> Union[Reply, AsyncGenerator[Reply, None]]:
        return_value = self._ask_impl(
            input,
            model,
            context,
            is_async=True,
            stream=stream,
            use_history=use_history,
            raise_errors=raise_errors,
        )
        if stream:
            return return_value
        return await return_value

    #
    # embed
    #
    def get_embed_size(self, model: Optional[LLMEmbeddingModel] = None) -> int:
        return self.EMBEDDING_DIMENSIONS[model or self.embedding_model]

    @property
    def embed_size(self) -> int:
        return self.get_embed_size()

    @abc.abstractmethod
    def embed(
        self,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModel] = None,
    ) -> Union[Embed, EmbedList]:
        pass

    @abc.abstractmethod
    async def embed_async(
        self,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModel] = None,
    ) -> Union[Embed, EmbedList]:
        pass


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
