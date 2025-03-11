import os

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.template import Template

from pyhub.llm import (
    AnthropicLLM,
    BaseLLM,
    GoogleLLM,
    OllamaLLM,
    OpenAILLM,
    SequentialChain,
    UpstageLLM,
)
from pyhub.llm.types import ChainReply, Reply
from pyhub.rag.settings import rag_settings


async def check_llm(llm: BaseLLM):
    errors = llm.check()
    if len(errors) > 0:
        msg = " ".join([str(e) for e in errors])
        pytest.skip(msg)
    else:
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


@pytest.mark.it("LLM에서 system_prompt에 Template 객체 렌더링 지원 테스트")
@pytest.mark.asyncio
async def test_openai_system_prompt_template():
    # Template 객체를 system_prompt로 사용
    llm = OpenAILLM(
        model="gpt-4o-mini",
        system_prompt=Template("당신은 {{ role }}입니다. {{ name }}님을 도와주세요."),
    )

    context = {"role": "친절한 비서", "name": "홍길동"}
    system_prompt = llm.get_system_prompt(context)
    human_prompt = llm.get_human_prompt("안녕하세요", context=context)

    assert "당신은 친절한 비서입니다. 홍길동님을 도와주세요." == system_prompt
    assert "안녕하세요" == human_prompt


@pytest.mark.asyncio
async def test_openai():
    llm = OpenAILLM()
    await check_llm(llm)


@pytest.mark.asyncio
async def test_upstage():
    llm = UpstageLLM()
    await check_llm(llm)


@pytest.mark.asyncio
async def test_anthropic():
    llm = AnthropicLLM()
    await check_llm(llm)


@pytest.mark.asyncio
async def test_ollama():
    llm = OllamaLLM()
    await check_llm(llm)


@pytest.mark.asyncio
async def test_google():
    llm = GoogleLLM()
    await check_llm(llm)


@pytest.mark.it("Django Template를 활용한 프롬프트 문자열 생성 테스트")
@pytest.mark.asyncio
async def test_template_prompt():
    llm_with_template = OpenAILLM(
        model="gpt-4o-mini",
        prompt=Template("오늘 {{ location }}의 날씨는 어떤가요?"),
    )
    errors = llm_with_template.check()
    if len(errors) > 0:
        msg = " ".join([str(e) for e in errors])
        pytest.skip(msg)
    else:
        # 템플릿 변수를 포함한 요청
        reply = llm_with_template.invoke({"location": "서울"})
        assert isinstance(reply, Reply)
        assert reply.text
        assert "Error" not in reply.text

        # 템플릿 변수가 올바르게 대체되었는지 확인
        messages = llm_with_template.history
        assert len(messages) == 2  # user/assistant 메시지
        assert "서울" in messages[-1].content

        # 스트리밍 모드에서도 템플릿 작동 확인
        stream_gen = llm_with_template.stream({"location": "부산"})
        stream_replies = [reply for reply in stream_gen]
        assert all(isinstance(reply, Reply) for reply in stream_replies)
        assert "Error" not in "".join(reply.text for reply in stream_replies)

        # 템플릿 변수가 올바르게 대체되었는지 확인
        messages = llm_with_template.history
        assert len(messages) == 4
        assert "부산" in messages[-1].content


@pytest.mark.it("LLM 체이닝 테스트")
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

    errors1 = llm_1.check()
    errors2 = llm_2.check()
    errors = errors1 + errors2
    if len(errors) > 0:
        msg = " ".join([str(e) for e in errors])
        pytest.skip(msg)
    else:
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
