import pytest

from pyhub.llm import AnthropicLLM, BaseLLM, GoogleLLM, OpenAILLM, UpstageLLM, SequentialChain
from pyhub.llm.types import Reply, ChainReply
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


@pytest.mark.asyncio
async def test_sequential_chain():
    # 첫 번째 LLM: 자장가 생성
    llm_1 = OpenAILLM(
        model="gpt-4o-mini",
        prompt="""
동화작가로서 지역 {location}과 주인공 이름 {name}을 이용해서
간단하고 짧은 (90개 단어 정도) 자장가를 하나 작성해줘.
""",
        output_key="자장가",
    )

    # 두 번째 LLM: 자장가 번역
    llm_2 = OpenAILLM(
        model="gpt-4o-mini",
        prompt="""
아래 자장가를 {language} 언어로 번역해줘.
번역할 때 어린이들이 좋아할 만한 단어들을 사용해야 하는 것을 잊지 말구.

<자장가>
{자장가}
</자장가>
    """,
        output_key="번역된_자장가",
    )

    # 체인 생성 및 실행
    chain = llm_1 | llm_2
    reply = chain.ask(
        {
            "location": "대한민국",
            "name": "영희",
            "language": "영어",
        }
    )

    # 검증
    assert isinstance(reply, ChainReply)
    assert len(reply) == 2  # 두 개의 LLM 응답이 있어야 함
    assert "자장가" in reply.values
    assert "번역된_자장가" in reply.values
    assert reply.text  # 마지막 응답이 비어있지 않아야 함

    # 파이프 연산자 대신 직접 SequentialChain 생성
    chain2 = SequentialChain(llm_1, llm_2)
    reply2 = chain2.ask(
        {
            "location": "제주도",
            "name": "철수",
            "language": "프랑스어",
        }
    )

    assert isinstance(reply2, ChainReply)
    assert len(reply2) == 2
    assert reply2.values["자장가"] != reply.values["자장가"]  # 다른 입력, 다른 출력
    assert reply2.values["번역된_자장가"] != reply.values["번역된_자장가"]
