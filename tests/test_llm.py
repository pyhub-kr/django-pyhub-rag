from typing import AsyncGenerator, Generator

import pytest

from pyhub.rag.llm import AnthropicLLM, GoogleLLM, OpenAILLM
from pyhub.rag.settings import rag_settings


@pytest.mark.asyncio
@pytest.mark.skipif(
    not rag_settings.openai_api_key or not rag_settings.openai_api_key.startswith("sk-"),
    reason="OpenAI API key not available",
)
async def test_openai():
    reply1 = OpenAILLM().reply("hello")
    assert isinstance(reply1, str)
    assert "Error" not in reply1

    reply2 = await OpenAILLM().areply("hello")
    assert isinstance(reply2, str)
    assert "Error" not in reply2

    # Test streaming
    stream1 = OpenAILLM().reply("hello", stream=True)
    assert isinstance(stream1, Generator)
    chunks1 = list(stream1)
    assert all(isinstance(chunk, str) for chunk in chunks1)
    assert "".join(chunks1)
    assert not any("Error" in chunk for chunk in chunks1)

    stream2 = await OpenAILLM().areply("hello", stream=True)
    assert isinstance(stream2, AsyncGenerator)
    chunks2 = [chunk async for chunk in stream2]
    assert all(isinstance(chunk, str) for chunk in chunks2)
    assert "".join(chunks2)
    assert not any("Error" in chunk for chunk in chunks2)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not rag_settings.anthropic_api_key or not rag_settings.anthropic_api_key.startswith("sk-ant-"),
    reason="Anthropic API key not available",
)
async def test_anthropic():
    reply1 = AnthropicLLM().reply("hello")
    assert isinstance(reply1, str)
    assert "Error" not in reply1

    reply2 = await AnthropicLLM().areply("hello")
    assert isinstance(reply2, str)
    assert "Error" not in reply1

    # Test streaming
    stream1 = AnthropicLLM().reply("hello", stream=True)
    assert isinstance(stream1, Generator)
    chunks1 = list(stream1)
    assert all(isinstance(chunk, str) for chunk in chunks1)
    assert "".join(chunks1)
    assert not any("Error" in chunk for chunk in chunks1), f"Error in chunks : {chunks1}"

    stream2 = await AnthropicLLM().areply("hello", stream=True)
    assert isinstance(stream2, AsyncGenerator)
    chunks2 = [chunk async for chunk in stream2]
    assert all(isinstance(chunk, str) for chunk in chunks2)
    assert "".join(chunks2)
    assert not any("Error" in chunk for chunk in chunks2), f"Error in chunks : {chunks2}"


@pytest.mark.asyncio
@pytest.mark.skipif(not rag_settings.google_api_key, reason="Google API key not available")
async def test_google():
    reply1 = GoogleLLM().reply("hello")
    assert isinstance(reply1, str)
    assert "Error" not in reply1

    reply2 = await GoogleLLM().areply("hello")
    assert isinstance(reply2, str)
    assert "Error" not in reply2

    # Test streaming
    stream1 = GoogleLLM().reply("hello", stream=True)
    assert isinstance(stream1, Generator)
    chunks1 = list(stream1)
    assert all(isinstance(chunk, str) for chunk in chunks1)
    assert "".join(chunks1)
    assert not any("Error" in chunk for chunk in chunks1)

    stream2 = await GoogleLLM().areply("hello", stream=True)
    assert isinstance(stream2, AsyncGenerator)
    chunks2 = [chunk async for chunk in stream2]
    assert all(isinstance(chunk, str) for chunk in chunks2)
    assert "".join(chunks2)
    assert not any("Error" in chunk for chunk in chunks2)
