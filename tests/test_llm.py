from typing import AsyncGenerator, Generator

import pytest

from pyhub.llm import AnthropicLLM, BaseLLM, GoogleLLM, OpenAILLM, UpstageLLM
from pyhub.llm.types import Reply
from pyhub.rag.settings import rag_settings


def check_reply(reply):
    assert isinstance(reply, Reply)
    assert "Error" not in reply.text


async def check_reply_generator(generator) -> str:
    assert isinstance(generator, (Generator, AsyncGenerator))
    if isinstance(generator, AsyncGenerator):
        reply_list = [reply async for reply in generator]
    else:
        reply_list = [reply for reply in generator]
    assert all(isinstance(reply, Reply) for reply in reply_list)
    assert not any("Error" in reply.text for reply in reply_list), f"Error in chunks : {reply_list}"
    reply_text = "".join(reply.text for reply in reply_list)
    assert len(reply_text) > 0
    return reply_text


async def check_llm(llm: BaseLLM):
    reply1 = llm.reply("hello. my name is tom.")
    check_reply(reply1)
    assert len(llm) == 2

    reply2 = await llm.areply("what is my name?")
    check_reply(reply2)
    assert "tom" in reply2.text.lower()
    assert len(llm) == 4

    llm.clear()
    assert len(llm) == 0

    gen1 = llm.reply("hello. my name is tom.", stream=True)
    await check_reply_generator(gen1)
    assert len(llm) == 2

    gen2 = await llm.areply("what is my name?", stream=True)
    reply_text = await check_reply_generator(gen2)
    assert "tom" in reply_text.lower()
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
