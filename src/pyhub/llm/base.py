import abc
import logging
from typing import AsyncGenerator, Generator, Optional, Union, cast

from .types import Embed, EmbedList, LLMChatModel, LLMEmbeddingModel, Message, Reply

logger = logging.getLogger(__name__)


class BaseLLM(abc.ABC):
    EMBEDDING_DIMENSIONS = {}

    def __init__(
        self,
        model: LLMChatModel = "gpt-4o-mini",
        embedding_model: LLMEmbeddingModel = "text-embedding-3-small",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[list[Message]] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.embedding_model = embedding_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.history = initial_messages or []
        self.api_key = api_key

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model}, embedding_model={self.embedding_model}, temperature={self.temperature}, max_tokens={self.max_tokens})"

    def __len__(self) -> int:
        return len(self.history)

    def clear(self):
        """Clear the chat history"""
        self.history = []

    @abc.abstractmethod
    def _make_ask(self, messages: list[Message], model: LLMChatModel) -> Reply:
        """Generate a response using the specific LLM provider"""
        pass

    @abc.abstractmethod
    async def _make_ask_async(self, messages: list[Message], model: LLMChatModel) -> Reply:
        """Generate a response asynchronously using the specific LLM provider"""
        pass

    @abc.abstractmethod
    def _make_ask_stream(self, messages: list[Message], model: LLMChatModel) -> Generator[Reply, None, None]:
        """Generate a streaming response using the specific LLM provider"""
        pass

    @abc.abstractmethod
    async def _make_ask_stream_async(
        self, messages: list[Message], model: LLMChatModel
    ) -> AsyncGenerator[Reply, None]:
        """Generate a streaming response asynchronously using the specific LLM provider"""
        pass

    def _prepare_messages(self, human_message: str, current_messages: list[Message]) -> list[Message]:
        if human_message:
            current_messages.append(Message(role="user", content=human_message))
        return current_messages

    def _update_history(self, human_message: str, ai_message: str) -> None:
        if human_message is not None:
            self.history.extend(
                [
                    Message(role="user", content=human_message),
                    Message(role="assistant", content=ai_message),
                ]
            )

    def _ask_impl(
        self,
        human_message: str,
        model: Optional[LLMChatModel] = None,
        *,
        raise_errors: bool = False,
        is_async: bool = False,
        use_history: bool = True,
    ):
        """동기 또는 비동기 응답을 생성하는 내부 메서드"""
        current_messages = [*self.history] if use_history else []
        current_model: LLMChatModel = cast(LLMChatModel, model or self.model)
        current_messages = self._prepare_messages(human_message, current_messages)

        async def async_handler() -> Reply:
            try:
                ask = await self._make_ask_async(current_messages, current_model)
            except Exception as e:
                if raise_errors:
                    raise e
                logger.error(f"Error occurred during API call: {str(e)}")
                return Reply(text=f"Error occurred during API call: {str(e)}")
            else:
                if use_history:
                    self._update_history(human_message, ask.text)
                return ask

        def sync_handler() -> Reply:
            try:
                ask = self._make_ask(current_messages, current_model)
            except Exception as e:
                if raise_errors:
                    raise e
                logger.error(f"Error occurred during API call: {str(e)}")
                return Reply(text=f"Error occurred during API call: {str(e)}")
            else:
                if use_history:
                    self._update_history(human_message, ask.text)
                return ask

        if is_async:
            return async_handler()
        else:
            return sync_handler()

    def _stream_ask_impl(
        self,
        human_message: str,
        model: Optional[LLMChatModel] = None,
        *,
        raise_errors: bool = False,
        is_async: bool = False,
        use_history: bool = True,
    ):
        """스트리밍 응답을 생성하는 내부 메서드 (동기/비동기)"""
        current_messages = [*self.history] if use_history else []
        current_model = cast(LLMChatModel, model or self.model)
        current_messages = self._prepare_messages(human_message, current_messages)

        async def async_stream_handler() -> AsyncGenerator[Reply, None]:
            try:
                text_list = []
                async for ask in self._make_ask_stream_async(current_messages, current_model):
                    text_list.append(ask.text)
                    yield ask

                if use_history:
                    full_text = "".join(text_list)
                    self._update_history(human_message, full_text)
            except Exception as e:
                if raise_errors:
                    raise e
                logger.error(f"Error occurred during streaming API call: {str(e)}")
                yield Reply(text=f"Error occurred during streaming API call: {str(e)}")

        def sync_stream_handler() -> Generator[Reply, None, None]:
            try:
                text_list = []
                for ask in self._make_ask_stream(current_messages, current_model):
                    text_list.append(ask.text)
                    yield ask

                if use_history:
                    full_text = "".join(text_list)
                    self._update_history(human_message, full_text)
            except Exception as e:
                if raise_errors:
                    raise e
                logger.error(f"Error occurred during streaming API call: {str(e)}")
                yield Reply(text=f"Error occurred during streaming API call: {str(e)}")

        if is_async:
            return async_stream_handler()
        else:
            return sync_stream_handler()

    def ask(
        self,
        human_message: str,
        model: Optional[LLMChatModel] = None,
        stream: bool = False,
        raise_errors: bool = False,
        use_history: bool = True,
    ) -> Union[Reply, Generator[str, None, None]]:
        if not stream:
            return self._ask_impl(
                human_message, model, raise_errors=raise_errors, is_async=False, use_history=use_history
            )
        return self._stream_ask_impl(
            human_message, model, raise_errors=raise_errors, is_async=False, use_history=use_history
        )

    async def aask(
        self,
        human_message: str,
        model: Optional[LLMChatModel] = None,
        stream: bool = False,
        raise_errors: bool = False,
        use_history: bool = True,
    ):
        if not stream:
            return await self._ask_impl(
                human_message, model, raise_errors=raise_errors, is_async=True, use_history=use_history
            )
        return self._stream_ask_impl(
            human_message, model, raise_errors=raise_errors, is_async=True, use_history=use_history
        )

    #
    # embed
    #
    def get_embed_size(self, model: Optional[LLMEmbeddingModel] = None) -> int:
        return self.EMBEDDING_DIMENSIONS[model or self.embedding_model]

    @property
    def embed_size(self):
        return self.get_embed_size()

    @abc.abstractmethod
    def embed(
        self,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModel] = None,
    ) -> Union[Embed, EmbedList]:
        pass

    @abc.abstractmethod
    async def aembed(
        self,
        input: Union[str, list[str]],
        model: Optional[LLMEmbeddingModel] = None,
    ) -> Union[Embed, EmbedList]:
        pass
