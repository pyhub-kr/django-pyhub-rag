from typing import AsyncGenerator, Generator

import pytest

from pyhub.llm import AnthropicLLM, BaseLLM, GoogleLLM, OpenAILLM, UpstageLLM
from pyhub.llm.types import Reply
from pyhub.rag.settings import rag_settings


def check_ask(ask):
    assert isinstance(ask, Reply)
    assert "Error" not in ask.text


async def check_ask_generator(generator) -> str:
    assert isinstance(generator, (Generator, AsyncGenerator))
    if isinstance(generator, AsyncGenerator):
        ask_list = [ask async for ask in generator]
    else:
        ask_list = [ask for ask in generator]
    assert all(isinstance(ask, Reply) for ask in ask_list)
    assert not any("Error" in ask.text for ask in ask_list), f"Error in chunks : {ask_list}"
    ask_text = "".join(ask.text for ask in ask_list)
    assert len(ask_text) > 0
    return ask_text


async def check_llm(llm: BaseLLM):
    ask1 = llm.ask("hello. my name is tom.")
    check_ask(ask1)
    assert len(llm) == 2

    ask2 = await llm.ask_async("what is my name?")
    check_ask(ask2)
    assert "tom" in ask2.text.lower()
    assert len(llm) == 4

    llm.clear()
    assert len(llm) == 0

    gen1 = llm.ask("hello. my name is tom.", stream=True)
    await check_ask_generator(gen1)
    assert len(llm) == 2

    gen2 = await llm.ask_async("what is my name?", stream=True)
    ask_text = await check_ask_generator(gen2)
    assert "tom" in ask_text.lower()
    assert len(llm) == 4


@pytest.mark.asyncio
@pytest.mark.skipif(
    not rag_settings.openai_api_key or not rag_settings.openai_api_key.startswith("sk-"),
    reason="OpenAI API key not available",
)
async def test_openai():
    llm = OpenAILLM()
    await check_llm(llm)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not rag_settings.upstage_api_key or not rag_settings.upstage_api_key.startswith("up_"),
    reason="Upstage API key not available",
)
async def test_upstage():
    llm = UpstageLLM()
    await check_llm(llm)


@pytest.mark.asyncio
@pytest.mark.skipif(
    not rag_settings.anthropic_api_key or not rag_settings.anthropic_api_key.startswith("sk-ant-"),
    reason="Anthropic API key not available",
)
async def test_anthropic():
    llm = AnthropicLLM()
    await check_llm(llm)


@pytest.mark.asyncio
@pytest.mark.skipif(not rag_settings.google_api_key, reason="Google API key not available")
async def test_google():
    llm = GoogleLLM()
    await check_llm(llm)
