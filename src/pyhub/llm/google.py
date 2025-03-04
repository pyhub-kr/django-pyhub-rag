from typing import AsyncGenerator, Generator, Optional, Union, cast

from google import genai
from google.genai.types import Content, GenerateContentConfig, Part

from pyhub.rag.settings import rag_settings

from .base import BaseLLM
from .types import (
    Embed,
    EmbedList,
    GoogleChatModel,
    GoogleEmbeddingModel,
    LLMEmbeddingModel,
    Message,
    Reply,
    Usage,
)


class GoogleLLM(BaseLLM):
    EMBEDDING_DIMENSIONS = {
        "text-embedding-004": 768,
    }

    def __init__(
        self,
        model: GoogleChatModel = "gemini-2.0-flash",
        embedding_model: GoogleEmbeddingModel = "text-embedding-004",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[list[Message]] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(
            model=model,
            embedding_model=embedding_model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            initial_messages=initial_messages,
            api_key=api_key or rag_settings.google_api_key,
        )

    def _make_reply(self, messages: list[Message], model: GoogleChatModel) -> Reply:
        client = genai.Client(api_key=self.api_key)

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
        usage = Usage(
            input=response.usage_metadata.prompt_token_count or 0,
            output=response.usage_metadata.candidates_token_count or 0,
        )
        return Reply(response.text, usage)

    async def _make_reply_async(self, messages: list[Message], model: GoogleChatModel) -> Reply:
        client = genai.Client(api_key=self.api_key)

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
        usage = Usage(
            input=response.usage_metadata.prompt_token_count or 0,
            output=response.usage_metadata.candidates_token_count or 0,
        )
        return Reply(response.text, usage)

    def _make_reply_stream(self, messages: list[Message], model: GoogleChatModel) -> Generator[Reply, None, None]:
        client = genai.Client(api_key=self.api_key)

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

        input_tokens = 0
        output_tokens = 0

        for chunk in response:
            yield Reply(text=chunk.text)
            input_tokens += chunk.usage_metadata.prompt_token_count or 0
            output_tokens += chunk.usage_metadata.candidates_token_count or 0

        usage = Usage(input=input_tokens, output=output_tokens)
        yield Reply(text="", usage=usage)

    async def _make_reply_stream_async(
        self, messages: list[Message], model: GoogleChatModel
    ) -> AsyncGenerator[Reply, None]:
        client = genai.Client(api_key=self.api_key)

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

        input_tokens = 0
        output_tokens = 0

        async for chunk in response:
            yield Reply(text=chunk.text)
            input_tokens += chunk.usage_metadata.prompt_token_count or 0
            output_tokens += chunk.usage_metadata.candidates_token_count or 0

        usage = Usage(input=input_tokens, output=output_tokens)
        yield Reply(text="", usage=usage)

    def reply(
        self,
        human_message: Optional[str] = None,
        model: Optional[GoogleChatModel] = None,
        stream: bool = False,
        raise_errors: bool = False,
    ) -> Reply:
        return super().reply(human_message, model, stream, raise_errors)

    async def areply(
        self,
        human_message: Optional[str] = None,
        model: Optional[GoogleChatModel] = None,
        stream: bool = False,
        raise_errors: bool = False,
    ) -> Reply:
        return await super().areply(human_message, model, stream, raise_errors)

    def embed(self, input: Union[str, list[str]], model: Optional[LLMEmbeddingModel] = None) -> Union[Embed, EmbedList]:
        embedding_model = cast(GoogleEmbeddingModel, model or self.embedding_model)

        client = genai.Client(api_key=self.api_key)
        response = client.models.embed_content(
            model=embedding_model,
            contents=input,
            # config=EmbedContentConfig(output_dimensionality=10),
        )
        usage = None  # TODO: response에 usage_metadata가 없음
        if isinstance(input, str):
            return Embed(response.embeddings[0].values, usage=usage)
        return EmbedList([Embed(v.values) for v in response.embeddings], usage=usage)

    async def aembed(
        self, input: Union[str, list[str]], model: Optional[LLMEmbeddingModel] = None
    ) -> Union[Embed, EmbedList]:
        embedding_model = cast(GoogleEmbeddingModel, model or self.embedding_model)

        client = genai.Client(api_key=self.api_key)
        response = await client.aio.models.embed_content(
            model=embedding_model,
            contents=input,
            # config=EmbedContentConfig(output_dimensionality=10),
        )
        usage = None  # TODO: response에 usage_metadata가 없음
        if isinstance(input, str):
            return Embed(response.embeddings[0].values, usage=usage)
        return EmbedList([Embed(v.values) for v in response.embeddings], usage=usage)


__all__ = ["GoogleLLM"]
