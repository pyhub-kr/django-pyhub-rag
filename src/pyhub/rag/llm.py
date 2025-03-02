import abc
import logging
from typing import AsyncGenerator, Generator, List, Literal, Optional, Union, cast

from anthropic import NOT_GIVEN as ANTHROPIC_NOT_GIVEN
from anthropic import Anthropic as SyncAnthropic
from anthropic import AsyncAnthropic
from anthropic.types import ModelParam as AnthropicChatModel
from google import genai
from google.genai.types import Content, GenerateContentConfig, Part
from openai import AsyncOpenAI
from openai import OpenAI as SyncOpenAI
from openai.types import ChatModel as OpenAIChatModel
from pydantic import BaseModel
from typing_extensions import TypeAlias

from pyhub.rag.settings import rag_settings


OpenAIEmbeddingModel: TypeAlias = Literal[
    "text-embedding-ada-002",  # 1536 차원
    "text-embedding-3-small",  # 1536 차원
    "text-embedding-3-large",  # 3072 차원
]

# https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings?hl=ko
GoogleEmbeddingModel: TypeAlias = Literal["text-embedding-004"]  # 768 차원

LLMEmbeddingModel = Union[OpenAIEmbeddingModel, GoogleEmbeddingModel]


# https://ai.google.dev/gemini-api/docs/models/gemini?hl=ko
GoogleChatModel: TypeAlias = Union[
    Literal[
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ],
]


LLMChatModel: TypeAlias = Union[OpenAIChatModel, AnthropicChatModel, GoogleChatModel]


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "function"]
    content: str


logger = logging.getLogger(__name__)


class LLM(abc.ABC):
    def __init__(
        self,
        model: LLMChatModel = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[List[Message]] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.history = initial_messages or []
        self.api_key = api_key

    @abc.abstractmethod
    def _generate_response(self, messages: list[Message], model: LLMChatModel) -> str:
        """Generate a response using the specific LLM provider"""
        pass

    @abc.abstractmethod
    async def _agenerate_response(self, messages: list[Message], model: LLMChatModel) -> str:
        """Generate a response asynchronously using the specific LLM provider"""
        pass

    @abc.abstractmethod
    def _generate_stream_response(self, messages: list[Message], model: LLMChatModel) -> Generator[str, None, None]:
        """Generate a streaming response using the specific LLM provider"""
        pass

    @abc.abstractmethod
    async def _agenerate_stream_response(
        self, messages: list[Message], model: LLMChatModel
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response asynchronously using the specific LLM provider"""
        pass

    @classmethod
    def create(cls, model: LLMChatModel, **kwargs) -> "LLM":
        """Factory method to create appropriate LLM instance based on model name"""
        if "claude" in model.lower():
            return AnthropicLLM(model=cast(AnthropicChatModel, model), **kwargs)
        elif "gemini" in model.lower():
            return GoogleLLM(model=cast(GoogleChatModel, model), **kwargs)
        else:  # Default to OpenAI
            return OpenAILLM(model=cast(OpenAIChatModel, model), **kwargs)

    def _prepare_messages(self, human_message: str, current_messages: List[Message]) -> List[Message]:
        if human_message is not None:
            current_messages.append(Message(role="user", content=human_message))
        return current_messages

    def _update_history(self, human_message: Optional[str], ai_message: str) -> None:
        if human_message is not None:
            self.history.extend(
                [
                    Message(role="user", content=human_message),
                    Message(role="assistant", content=ai_message),
                ]
            )

    def _reply_impl(
        self,
        human_message: Optional[str] = None,
        model: Optional[LLMChatModel] = None,
        *,
        is_async: bool = False,
    ) -> Union[str, "asyncio.Future[str]"]:
        """동기 또는 비동기 응답을 생성하는 내부 메서드"""
        current_messages = [*self.history]
        current_model = model or self.model
        current_messages = self._prepare_messages(human_message, current_messages)

        async def async_handler() -> str:
            try:
                ai_message = await self._agenerate_response(current_messages, current_model)
            except Exception as e:
                logger.error(f"Error occurred during API call: {str(e)}")
                return f"Error occurred during API call: {str(e)}"
            else:
                self._update_history(human_message, ai_message)
                return ai_message

        def sync_handler() -> str:
            try:
                ai_message = self._generate_response(current_messages, current_model)
            except Exception as e:
                logger.error(f"Error occurred during API call: {str(e)}")
                return f"Error occurred during API call: {str(e)}"
            else:
                self._update_history(human_message, ai_message)
                return ai_message

        if is_async:
            return async_handler()
        else:
            return sync_handler()

    def reply(
        self,
        human_message: Optional[str] = None,
        model: Optional[LLMChatModel] = None,
        stream: bool = False,
    ) -> Union[str, Generator[str, None, None]]:
        if not stream:
            return self._reply_impl(human_message, model, is_async=False)
        return self._stream_reply_impl(human_message, model, is_async=False)

    async def areply(
        self,
        human_message: Optional[str] = None,
        model: Optional[LLMChatModel] = None,
        stream: bool = False,
    ) -> Union[str, AsyncGenerator[str, None]]:
        if not stream:
            return await self._reply_impl(human_message, model, is_async=True)
        return self._stream_reply_impl(human_message, model, is_async=True)

    def _stream_reply_impl(
        self,
        human_message: Optional[str] = None,
        model: Optional[LLMChatModel] = None,
        *,
        is_async: bool = False,
    ) -> Union[Generator[str, None, None], AsyncGenerator[str, None]]:
        """스트리밍 응답을 생성하는 내부 메서드 (동기/비동기)"""
        current_messages = [*self.history]
        current_model = model or self.model
        current_messages = self._prepare_messages(human_message, current_messages)

        async def async_stream_handler() -> AsyncGenerator[str, None]:
            try:
                async for chunk in self._agenerate_stream_response(current_messages, current_model):
                    yield chunk

                # Get the full response to update history
                full_response = "".join(
                    [chunk async for chunk in self._agenerate_stream_response(current_messages, current_model)]
                )
                self._update_history(human_message, full_response)
            except Exception as e:
                logger.error(f"Error occurred during streaming API call: {str(e)}")
                yield f"Error occurred during streaming API call: {str(e)}"

        def sync_stream_handler() -> Generator[str, None, None]:
            try:
                for chunk in self._generate_stream_response(current_messages, current_model):
                    yield chunk

                # Get the full response to update history
                full_response = "".join(list(self._generate_stream_response(current_messages, current_model)))
                self._update_history(human_message, full_response)
            except Exception as e:
                logger.error(f"Error occurred during streaming API call: {str(e)}")
                yield f"Error occurred during streaming API call: {str(e)}"

        if is_async:
            return async_stream_handler()
        else:
            return sync_stream_handler()


class OpenAILLM(LLM):
    def __init__(
        self,
        model: OpenAIChatModel = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[List[Message]] = None,
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

    def _generate_response(self, messages: list[Message], model: LLMChatModel) -> str:
        sync_client = SyncOpenAI(api_key=self.api_key or rag_settings.openai_api_key)
        request_params = self._prepare_openai_request(messages, model)
        response = sync_client.chat.completions.create(**request_params)
        return response.choices[0].message.content

    async def _agenerate_response(self, messages: list[Message], model: LLMChatModel) -> str:
        async_client = AsyncOpenAI(api_key=self.api_key or rag_settings.openai_api_key)
        request_params = self._prepare_openai_request(messages, model)
        response = await async_client.chat.completions.create(**request_params)
        return response.choices[0].message.content

    def _generate_stream_response(self, messages: list[Message], model: LLMChatModel) -> Generator[str, None, None]:
        sync_client = SyncOpenAI(api_key=self.api_key or rag_settings.openai_api_key)
        request_params = self._prepare_openai_request(messages, model)
        request_params["stream"] = True

        response_stream = sync_client.chat.completions.create(**request_params)
        for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _agenerate_stream_response(
        self, messages: list[Message], model: LLMChatModel
    ) -> AsyncGenerator[str, None]:
        async_client = AsyncOpenAI(api_key=self.api_key or rag_settings.openai_api_key)
        request_params = self._prepare_openai_request(messages, model)
        request_params["stream"] = True

        response_stream = await async_client.chat.completions.create(**request_params)
        async for chunk in response_stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def reply(
        self,
        human_message: Optional[str] = None,
        model: Optional[OpenAIChatModel] = None,
        stream: bool = False,
    ) -> str:
        return super().reply(human_message, model, stream)

    async def areply(
        self,
        human_message: Optional[str] = None,
        model: Optional[OpenAIChatModel] = None,
        stream: bool = False,
    ) -> str:
        return await super().areply(human_message, model, stream)


class AnthropicLLM(LLM):
    def __init__(
        self,
        model: AnthropicChatModel = "claude-3-5-haiku-latest",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[List[Message]] = None,
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

    def _generate_response(self, messages: list[Message], model: AnthropicChatModel) -> str:
        sync_client = SyncAnthropic(api_key=self.api_key or rag_settings.anthropic_api_key)
        response = sync_client.messages.create(
            model=model,
            system=self.system_prompt or ANTHROPIC_NOT_GIVEN,
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.content[0].text

    async def _agenerate_response(self, messages: list[Message], model: AnthropicChatModel) -> str:
        async_client = AsyncAnthropic(api_key=self.api_key or rag_settings.anthropic_api_key)
        response = await async_client.messages.create(
            model=model,
            system=self.system_prompt,
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.content[0].text

    def _generate_stream_response(
        self, messages: list[Message], model: AnthropicChatModel
    ) -> Generator[str, None, None]:
        sync_client = SyncAnthropic(api_key=self.api_key or rag_settings.anthropic_api_key)
        response = sync_client.messages.create(
            model=model,
            system=self.system_prompt or ANTHROPIC_NOT_GIVEN,
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        for chunk in response:
            if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                yield chunk.delta.text
            elif hasattr(chunk, "type") and chunk.type == "content_block_delta":
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    yield chunk.delta.text
                elif hasattr(chunk, "content_block") and hasattr(chunk.content_block, "text"):
                    yield chunk.content_block.text

    async def _agenerate_stream_response(
        self, messages: list[Message], model: AnthropicChatModel
    ) -> AsyncGenerator[str, None]:
        async_client = AsyncAnthropic(api_key=self.api_key or rag_settings.anthropic_api_key)
        response = await async_client.messages.create(
            model=model,
            system=self.system_prompt or ANTHROPIC_NOT_GIVEN,
            messages=[dict(message) for message in messages],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        async for chunk in response:
            # 이벤트 타입에 따라 처리
            if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                yield chunk.delta.text
            elif hasattr(chunk, "type") and chunk.type == "content_block_delta":
                if hasattr(chunk, "delta") and hasattr(chunk.delta, "text"):
                    yield chunk.delta.text
                elif hasattr(chunk, "content_block") and hasattr(chunk.content_block, "text"):
                    yield chunk.content_block.text

    def reply(
        self,
        human_message: Optional[str] = None,
        model: Optional[AnthropicChatModel] = None,
        stream: bool = False,
    ) -> str:
        return super().reply(human_message, model, stream)

    async def areply(
        self,
        human_message: Optional[str] = None,
        model: Optional[AnthropicChatModel] = None,
        stream: bool = False,
    ) -> str:
        return await super().areply(human_message, model, stream)


class GoogleLLM(LLM):
    def __init__(
        self,
        model: GoogleChatModel = "gemini-2.0-flash",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[List[Message]] = None,
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

    def _generate_response(self, messages: list[Message], model: GoogleChatModel) -> str:
        api_key: str = self.api_key or rag_settings.google_api_key
        client = genai.Client(api_key=api_key)

        contents: list[Content] = [
            Content(
                role="user" if message.role == "user" else "model",
                parts=[Part(text=message.content)],
            )
            for message in messages
        ]

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=self.system_prompt,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            ),
        )
        return response.text

    async def _agenerate_response(self, messages: list[Message], model: GoogleChatModel) -> str:
        api_key: str = self.api_key or rag_settings.google_api_key
        client = genai.Client(api_key=api_key)

        contents: list[Content] = [
            Content(
                role="user" if message.role == "user" else "model",
                parts=[Part(text=message.content)],
            )
            for message in messages
        ]

        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=self.system_prompt,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            ),
        )
        return response.text

    def _generate_stream_response(self, messages: list[Message], model: GoogleChatModel) -> Generator[str, None, None]:
        api_key: str = self.api_key or rag_settings.google_api_key
        client = genai.Client(api_key=api_key)

        contents: list[Content] = [
            Content(
                role="user" if message.role == "user" else "model",
                parts=[Part(text=message.content)],
            )
            for message in messages
        ]

        response = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=self.system_prompt,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            ),
        )
        # Stream 처리를 위해 응답 객체의 iterator를 사용
        for chunk in response:
            yield chunk.text

    async def _agenerate_stream_response(
        self, messages: list[Message], model: GoogleChatModel
    ) -> AsyncGenerator[str, None]:
        api_key: str = self.api_key or rag_settings.google_api_key
        client = genai.Client(api_key=api_key)

        contents: list[Content] = [
            Content(
                role="user" if message.role == "user" else "model",
                parts=[Part(text=message.content)],
            )
            for message in messages
        ]

        response = await client.aio.models.generate_content_stream(
            model=model,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=self.system_prompt,
                max_output_tokens=self.max_tokens,
                temperature=self.temperature,
            ),
        )
        # 비동기 스트림 처리
        async for chunk in response:
            yield chunk.text

    def reply(
        self,
        human_message: Optional[str] = None,
        model: Optional[GoogleChatModel] = None,
        stream: bool = False,
    ) -> str:
        return super().reply(human_message, model, stream)

    async def areply(
        self,
        human_message: Optional[str] = None,
        model: Optional[GoogleChatModel] = None,
        stream: bool = False,
    ) -> str:
        return await super().areply(human_message, model, stream)
