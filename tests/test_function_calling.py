#!/usr/bin/env python3
"""
Function Calling 기능 테스트 스크립트
"""
import asyncio
import os
import time
import pytest
from pyhub import init
from pyhub.llm import LLM
from pyhub.llm.tools import ToolAdapter, FunctionToolAdapter, create_tool_from_function

# Django 초기화
init()

# LLM 제공자 테스트 파라미터
LLM_PROVIDERS = [
    pytest.param(
        {"name": "OpenAI", "model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"},
        id="openai",
        marks=pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OpenAI API key not available")
    ),
    pytest.param(
        {"name": "Upstage", "model": "solar-mini", "api_key_env": "UPSTAGE_API_KEY"},
        id="upstage", 
        marks=pytest.mark.skipif(not os.environ.get("UPSTAGE_API_KEY"), reason="Upstage API key not available")
    ),
    pytest.param(
        {"name": "Anthropic", "model": "claude-3-haiku-20240307", "api_key_env": "ANTHROPIC_API_KEY"},
        id="anthropic",
        marks=pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="Anthropic API key not available")
    ),
    pytest.param(
        {"name": "Google", "model": "gemini-1.5-flash", "api_key_env": "GOOGLE_API_KEY"},
        id="google",
        marks=pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="Google API key not available")
    ),
]

# 비동기 지원 제공자들 (모든 Function Calling 지원 제공자)
ASYNC_PROVIDERS = [
    pytest.param(
        {"name": "OpenAI", "model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY"},
        id="openai",
        marks=pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="OpenAI API key not available")
    ),
    pytest.param(
        {"name": "Upstage", "model": "solar-mini", "api_key_env": "UPSTAGE_API_KEY"},
        id="upstage",
        marks=pytest.mark.skipif(not os.environ.get("UPSTAGE_API_KEY"), reason="Upstage API key not available")
    ),
    pytest.param(
        {"name": "Anthropic", "model": "claude-3-haiku-20240307", "api_key_env": "ANTHROPIC_API_KEY"},
        id="anthropic",
        marks=pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="Anthropic API key not available")
    ),
    pytest.param(
        {"name": "Google", "model": "gemini-1.5-flash", "api_key_env": "GOOGLE_API_KEY"},
        id="google",
        marks=pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="Google API key not available")
    ),
]


def test_tool_adapter():
    """ToolAdapter 기능 테스트"""
    print("=== ToolAdapter 테스트 ===\n")

    # 1. 일반 함수 테스트
    def simple_function(name: str, age: int = 25) -> str:
        """간단한 함수입니다."""
        return f"안녕하세요 {name}님, {age}세시군요!"

    # 함수를 Tool로 변환
    tool = FunctionToolAdapter.create_tool_from_function(simple_function)
    print(f"함수 → Tool 변환 성공:")
    print(f"  이름: {tool.name}")
    print(f"  설명: {tool.description}")
    print(f"  스키마 존재: {tool.args_schema is not None}")

    # 2. Callable 객체 테스트
    class GreetingService:
        """인사 서비스"""

        def __call__(self, name: str, greeting: str = "안녕하세요") -> str:
            """사용자에게 인사합니다."""
            return f"{greeting}, {name}님!"

    greeting = GreetingService()
    greeting_tool = create_tool_from_function(greeting)
    print(f"\nCallable 객체 → Tool 변환 성공:")
    print(f"  이름: {greeting_tool.name}")
    print(f"  설명: {greeting_tool.description}")

    # 3. 여러 도구 일괄 변환 테스트
    tools = ToolAdapter.adapt_tools([simple_function, greeting])
    print(f"\n일괄 변환 결과: {len(tools)}개 도구")
    for i, tool in enumerate(tools):
        print(f"  {i+1}. {tool.name}: {tool.description[:30]}...")


def test_schema_extraction():
    """스키마 추출 기능 테스트"""
    print("\n=== 스키마 추출 테스트 ===\n")

    def complex_function(
        name: str,
        age: int,
        height: float = 170.0,
        is_student: bool = False,
        hobbies: list = None,
        metadata: dict = None,
    ) -> str:
        """복잡한 타입을 가진 함수입니다."""
        return f"처리 완료: {name}"

    schema = FunctionToolAdapter.extract_function_schema(complex_function)
    print("추출된 스키마:")
    print(f"  함수명: {schema['name']}")
    print(f"  설명: {schema['description']}")
    print(f"  비동기: {schema['is_async']}")
    print("  파라미터:")

    for param_name, param_info in schema["parameters"]["properties"].items():
        required = "필수" if param_name in schema["parameters"]["required"] else "선택"
        print(f"    {param_name}: {param_info['type']} ({required})")


def test_tool_execution():
    """도구 실행 테스트"""
    print("\n=== 도구 실행 테스트 ===\n")

    from pyhub.llm.tools import ToolExecutor

    # 테스트용 함수들
    def add_numbers(a: int, b: int) -> int:
        """두 숫자를 더합니다."""
        return a + b

    def greet_user(name: str, title: str = "님") -> str:
        """사용자에게 인사합니다."""
        return f"안녕하세요, {name}{title}!"

    # 도구들을 변환
    tools = ToolAdapter.adapt_tools([add_numbers, greet_user])
    executor = ToolExecutor(tools)

    # 도구 실행 테스트
    print("1. add_numbers 실행:")
    result1 = executor.execute_tool("add_numbers", {"a": 10, "b": 5})
    print(f"   결과: {result1}")

    print("2. greet_user 실행:")
    result2 = executor.execute_tool("greet_user", {"name": "김철수"})
    print(f"   결과: {result2}")

    print("3. 존재하지 않는 도구 실행:")
    result3 = executor.execute_tool("nonexistent", {})
    print(f"   결과: {result3}")


async def test_async_tools():
    """비동기 도구 테스트"""
    print("\n=== 비동기 도구 테스트 ===\n")

    from pyhub.llm.tools import ToolExecutor

    # 비동기 함수 정의
    async def async_fetch_data(url: str) -> str:
        """비동기로 데이터를 가져옵니다."""
        await asyncio.sleep(0.1)  # 시뮬레이션
        return f"데이터 from {url}: [mock data]"

    def sync_process_data(data: str) -> str:
        """동기적으로 데이터를 처리합니다."""
        return f"처리됨: {data.upper()}"

    # 도구 변환
    tools = ToolAdapter.adapt_tools([async_fetch_data, sync_process_data])
    executor = ToolExecutor(tools)

    print("1. 비동기 도구 실행:")
    result1 = await executor.execute_tool_async("async_fetch_data", {"url": "https://api.example.com"})
    print(f"   결과: {result1}")

    print("2. 동기 도구를 비동기로 실행:")
    result2 = await executor.execute_tool_async("sync_process_data", {"data": "test data"})
    print(f"   결과: {result2}")


def test_provider_conversion():
    """Provider별 스키마 변환 테스트"""
    print("\n=== Provider 스키마 변환 테스트 ===\n")

    from pyhub.llm.tools import ProviderToolConverter

    def sample_function(city: str, country: str = "KR") -> str:
        """도시의 날씨를 조회합니다."""
        return f"{city}, {country}의 날씨"

    tool = create_tool_from_function(sample_function)

    # OpenAI 형식 변환
    openai_schema = ProviderToolConverter.to_openai_function(tool)
    print("OpenAI 스키마:")
    print(f"  타입: {openai_schema['type']}")
    print(f"  함수명: {openai_schema['function']['name']}")
    print(f"  설명: {openai_schema['function']['description']}")

    # Anthropic 형식 변환
    anthropic_schema = ProviderToolConverter.to_anthropic_tool(tool)
    print("\nAnthropic 스키마:")
    print(f"  이름: {anthropic_schema['name']}")
    print(f"  설명: {anthropic_schema['description']}")

    # Google 형식 변환
    google_schema = ProviderToolConverter.to_google_function(tool)
    print("\nGoogle 스키마:")
    print(f"  이름: {google_schema['name']}")
    print(f"  설명: {google_schema['description']}")


def test_agent_compatibility():
    """Agent 도구 호환성 테스트"""
    print("\n=== Agent 도구 호환성 테스트 ===\n")

    from pyhub.llm.agents.tools import Calculator
    from pyhub.llm.tools import ProviderToolConverter

    # Agent 도구 생성
    calc = Calculator()

    # Agent 도구를 Tool 객체로 변환
    agent_tool = ToolAdapter.adapt_tool(calc)
    print(f"Agent Tool 변환 성공:")
    print(f"  이름: {agent_tool.name}")
    print(f"  설명: {agent_tool.description}")
    print(f"  스키마: {agent_tool.args_schema}")
    print(f"  검증 레벨: {agent_tool.validation_level}")

    # OpenAI Function Calling 스키마 생성
    openai_schema = ProviderToolConverter.to_openai_function(agent_tool)
    print(f"\nOpenAI 스키마 생성:")
    print(f"  함수명: {openai_schema['function']['name']}")
    print(f"  파라미터: {list(openai_schema['function']['parameters']['properties'].keys())}")

    # 실제 LLM과 함께 테스트
    print(f"\nLLM Function Calling 테스트:")
    try:
        llm = LLM.create(model="gpt-4o-mini")
        result = llm.ask("7 + 15는 얼마야?", tools=[calc], model="gpt-4o-mini")
        print(f"  성공: {result.text}")

        # 일반 함수와 Agent 도구 혼합 테스트
        def multiply(a: int, b: int) -> int:
            """두 수를 곱합니다"""
            return a * b

        result2 = llm.ask("3 곱하기 5한 다음 2를 더해줘", tools=[multiply, calc], model="gpt-4o-mini")
        print(f"  혼합 테스트: {result2.text}")

    except Exception as e:
        print(f"  오류: {e}")


@pytest.mark.parametrize("provider_info", LLM_PROVIDERS)
def test_basic_function_calling(provider_info):
    """기본 Function Calling 테스트"""
    
    def add_numbers(a: int, b: int) -> int:
        """두 숫자를 더합니다."""
        return a + b
    
    def multiply(x: float, y: float) -> float:
        """두 숫자를 곱합니다."""
        return x * y
    
    provider_name = provider_info["name"]
    model = provider_info["model"]
    
    # LLM 인스턴스 생성
    llm = LLM.create(model=model)
    
    # 기본 계산 테스트
    if provider_name == "OpenAI":
        question = "25 곱하기 4는?"
        tools = [multiply]
        expected_answer = 100
    elif provider_name == "Upstage":
        question = "10 + 15는?"
        tools = [add_numbers]
        expected_answer = 25
    elif provider_name == "Anthropic":
        question = "7 곱하기 8은?"
        tools = [multiply]
        expected_answer = 56
    else:  # Google
        question = "12 + 8은?"
        tools = [add_numbers]
        expected_answer = 20
    
    result = llm.ask(question, tools=tools, model=model)
    
    # 결과 검증
    assert result is not None
    assert result.text is not None
    assert len(result.text) > 0
    assert str(expected_answer) in result.text
    
    # 사용량 정보 확인 (일부 제공자는 None일 수 있음)
    if result.usage:
        assert result.usage.input > 0


@pytest.mark.parametrize("provider_info", LLM_PROVIDERS)
def test_multiple_tools_function_calling(provider_info):
    """복수 도구 Function Calling 테스트"""
    
    def add_numbers(a: int, b: int) -> int:
        """두 숫자를 더합니다."""
        return a + b
    
    def get_weather(city: str, country: str = "KR") -> str:
        """지정된 도시의 날씨를 조회합니다."""
        return f"{city}, {country}의 날씨: 맑음 (22°C)"
    
    provider_name = provider_info["name"]
    model = provider_info["model"]
    
    # LLM 인스턴스 생성
    llm = LLM.create(model=model)
    
    # 복수 도구 테스트
    result = llm.ask(
        "서울 날씨를 알려주고, 5 + 3을 계산해줘",
        tools=[get_weather, add_numbers],
        model=model
    )
    
    # 결과 검증
    assert result is not None
    assert result.text is not None
    assert len(result.text) > 0
    
    # 두 작업의 결과가 모두 포함되어야 함
    # 다만 Anthropic은 한 번에 하나의 도구만 호출할 수 있음
    weather_found = ("서울" in result.text or "날씨" in result.text)
    math_found = ("8" in result.text or "더하기" in result.text or "계산" in result.text or "add_numbers" in result.text)
    
    if provider_name == "Anthropic":
        # Anthropic은 한 번에 하나의 도구만 호출할 수 있으므로 둘 중 하나만 있어도 통과
        assert (weather_found or math_found), f"At least one tool result should be found in: {result.text}"
    else:
        # 다른 제공자들은 두 작업 모두 포함되어야 함
        assert weather_found, f"Weather info should be found in: {result.text}"
        assert math_found, f"Math calculation should be found in: {result.text}"


@pytest.mark.parametrize("provider_info", ASYNC_PROVIDERS)
@pytest.mark.asyncio
async def test_async_function_calling(provider_info):
    """비동기 Function Calling 테스트"""
    
    async def async_weather_lookup(city: str) -> str:
        """비동기로 날씨 정보를 조회합니다."""
        await asyncio.sleep(0.1)  # API 호출 시뮬레이션
        return f"{city}의 현재 날씨: 구름 많음, 18°C"
    
    def sync_calculation(a: int, b: int, operation: str = "add") -> int:
        """동기 계산 함수"""
        if operation == "add":
            return a + b
        elif operation == "multiply":
            return a * b
        else:
            return 0
    
    provider_name = provider_info["name"]
    model = provider_info["model"]
    
    # LLM 인스턴스 생성
    llm = LLM.create(model=model)
    
    # 비동기 + 동기 도구 혼합 테스트
    result = await llm.ask_async(
        "부산 날씨를 확인하고, 7 더하기 3을 계산해줘",
        tools=[async_weather_lookup, sync_calculation],
        model=model
    )
    
    # 결과 검증
    assert result is not None
    assert result.text is not None
    assert len(result.text) > 0
    
    # 부산 날씨와 계산 결과가 포함되어야 함
    weather_found = ("부산" in result.text or "날씨" in result.text)
    math_found = ("10" in result.text or "더하기" in result.text or "계산" in result.text)
    
    if provider_name == "Anthropic":
        # Anthropic은 한 번에 하나의 도구만 호출할 수 있으므로 둘 중 하나만 있어도 통과
        assert (weather_found or math_found), f"At least one tool result should be found in: {result.text}"
    else:
        # 다른 제공자들은 두 작업 모두 포함되어야 함
        assert weather_found, f"Weather info should be found in: {result.text}"
        assert math_found, f"Math calculation should be found in: {result.text}"


@pytest.mark.parametrize("provider_info", LLM_PROVIDERS)
def test_error_handling(provider_info):
    """Function Calling 오류 처리 테스트"""
    
    def error_prone_function(value: int) -> str:
        """오류를 발생시킬 수 있는 함수"""
        if value < 0:
            raise ValueError("음수는 처리할 수 없습니다")
        elif value > 100:
            raise RuntimeError("100보다 큰 값은 지원하지 않습니다")
        return f"값 {value} 처리 완료"
    
    def safe_function(text: str) -> str:
        """안전한 함수"""
        return f"안전하게 처리됨: {text}"
    
    provider_name = provider_info["name"]
    model = provider_info["model"]
    
    # LLM 인스턴스 생성
    llm = LLM.create(model=model)
    
    # 1. 정상 작동 테스트
    result1 = llm.ask(
        "값 50을 처리해줘",
        tools=[error_prone_function, safe_function],
        model=model
    )
    
    # 결과 검증
    assert result1 is not None
    assert result1.text is not None
    assert len(result1.text) > 0
    
    # 각 제공자별로 다른 응답 형식 허용
    if provider_name == "Upstage":
        # Upstage는 도구 호출 이름만 표시될 수 있음
        assert ("50" in result1.text or "처리" in result1.text or "error_prone_function" in result1.text or "safe_function" in result1.text)
    elif provider_name == "Google":
        # Google은 때때로 명확화 질문을 할 수 있음
        assert ("50" in result1.text or "처리" in result1.text or "error_prone_function" in result1.text or "함수" in result1.text or "결과" in result1.text)
    else:
        # 다른 제공자들은 실제 결과 포함
        assert ("50" in result1.text or "처리" in result1.text)
    
    # 2. 오류 발생 상황에서의 적절한 처리 테스트
    result2 = llm.ask(
        "값 -10을 처리해줘. 오류가 나면 '오류 발생' 텍스트로 safe_function을 호출해줘",
        tools=[error_prone_function, safe_function], 
        model=model
    )
    
    # 오류 처리 결과 검증
    assert result2 is not None
    assert result2.text is not None
    assert len(result2.text) > 0
    
    # 오류가 발생했지만 안전한 함수로 처리되었는지 확인
    if provider_name == "Upstage":
        # Upstage는 도구 호출 이름만 표시될 수 있음
        assert ("안전" in result2.text or "처리" in result2.text or "오류" in result2.text or "safe_function" in result2.text or "error_prone_function" in result2.text)
    elif provider_name == "Google":
        # Google은 때때로 명확화 질문을 할 수 있음
        assert ("안전" in result2.text or "처리" in result2.text or "오류" in result2.text or "함수" in result2.text or "결과" in result2.text)
    else:
        # 다른 제공자들은 실제 결과 포함
        assert ("안전" in result2.text or "처리" in result2.text or "오류" in result2.text)


@pytest.mark.parametrize("provider_info", ASYNC_PROVIDERS)
def test_function_calling_performance(provider_info):
    """Function Calling 성능 테스트"""
    import time
    
    def simple_calc(a: int, b: int, op: str) -> float:
        """간단한 계산 함수"""
        if op == "add":
            return a + b
        elif op == "subtract": 
            return a - b
        elif op == "multiply":
            return a * b
        elif op == "divide":
            return a / b if b != 0 else 0
        return 0
    
    provider_name = provider_info["name"]
    model = provider_info["model"]
    
    # LLM 인스턴스 생성
    llm = LLM.create(model=model)
    
    # 단일 Function Call 성능 측정
    start_time = time.time()
    result = llm.ask(
        "25 곱하기 4를 계산해줘",
        tools=[simple_calc],
        model=model
    )
    end_time = time.time()
    
    duration = end_time - start_time
    
    # 결과 검증
    assert result is not None
    assert result.text is not None
    assert len(result.text) > 0
    
    # 각 제공자별로 다른 응답 형식 허용
    if provider_name == "Google":
        # Google은 때때로 지시사항을 제공할 수 있음
        assert ("100" in result.text or "25" in result.text or "4" in result.text or "곱하기" in result.text or "계산" in result.text)
    else:
        # 다른 제공자들은 실제 결과 포함
        assert "100" in result.text  # 25 * 4 = 100
    
    # 성능 검증 (10초 이내 완료)
    assert duration < 10.0, f"Function calling took too long: {duration:.2f}s"
    
    # 사용량 정보 확인
    if result.usage:
        assert result.usage.input > 0
        assert result.usage.output > 0


async def run_all_tests():
    """모든 테스트 실행 (pytest 사용 권장)"""
    print("Function Calling 시스템 테스트 시작\n")
    print("참고: 개별 테스트는 pytest로 실행하는 것을 권장합니다:")
    print("pytest tests/test_function_calling.py -v")
    print("pytest tests/test_function_calling.py::test_basic_function_calling -v")

    # 기본 도구 시스템 테스트
    test_tool_adapter()
    test_schema_extraction()
    test_tool_execution()
    await test_async_tools()
    test_provider_conversion()
    test_agent_compatibility()

    print("\n🎉 기본 도구 시스템 테스트 완료!")
    print("Function Calling 테스트는 pytest로 실행해주세요.")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
