import pytest

from pyhub.llm import AnthropicLLM, BaseLLM, GoogleLLM, OpenAILLM, UpstageLLM
from pyhub.llm.types import Reply
from pyhub.rag.settings import rag_settings


async def check_llm(llm: BaseLLM):
    ask1 = llm.ask("hello. my name is tom.")
    assert isinstance(ask1, Reply)
    assert "Error" not in ask1.text
    assert len(llm) == 2

    ask2 = await llm.ask_async("what is my name?")
    assert isinstance(ask2, Reply)
    assert "Error" not in ask2.text
    assert "tom" in ask2.text.lower()
    assert len(llm) == 4

    llm.clear()
    assert len(llm) == 0

    gen1 = llm.ask("hello. my name is tom.", stream=True)
    reply_list1 = [reply for reply in gen1]
    assert all([isinstance(reply, Reply) for reply in reply_list1])
    assert "Error" not in "".join([reply.text for reply in reply_list1])
    assert len(llm) == 2

    gen2 = await llm.ask_async("hello. my name is tom.", stream=True)
    reply_list2 = [reply async for reply in gen2]
    assert all([isinstance(reply, Reply) for reply in reply_list2])
    assert "Error" not in "".join([reply.text for reply in reply_list2])
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
