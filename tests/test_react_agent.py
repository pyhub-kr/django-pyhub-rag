"""Tests for React Agent implementation."""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

from pyhub.llm.agents import Tool, BaseTool
from pyhub.llm.agents.react import (
    ReactAgent,
    AsyncReactAgent,
    create_react_agent,
    parse_react_output,
    ReactStep,
)
from pyhub.llm.agents.tools import Calculator


class TestReactOutputParsing:
    """React 출력 파싱 테스트"""
    
    def test_parse_thought_action_observation(self):
        """Thought/Action/Observation 파싱 테스트"""
        output = """
        Thought: I need to calculate 2 + 2
        Action: calculator
        Action Input: {"expression": "2 + 2"}
        """
        
        step = parse_react_output(output)
        assert step.thought == "I need to calculate 2 + 2"
        assert step.action == "calculator"
        assert step.action_input == {"expression": "2 + 2"}
        assert step.is_final is False
    
    def test_parse_final_answer(self):
        """Final Answer 파싱 테스트"""
        output = """
        Thought: I now have the answer
        Final Answer: The result is 4.
        """
        
        step = parse_react_output(output)
        assert step.thought == "I now have the answer"
        assert step.final_answer == "The result is 4."
        assert step.is_final is True
    
    def test_parse_with_observation(self):
        """Observation 포함 파싱 테스트"""
        output = """
        Thought: Let me calculate this
        Action: calculator
        Action Input: {"expression": "10 * 5"}
        Observation: 50
        """
        
        step = parse_react_output(output)
        assert step.thought == "Let me calculate this"
        assert step.action == "calculator"
        assert step.action_input == {"expression": "10 * 5"}
        assert step.observation == "50"
    
    def test_parse_multiline_content(self):
        """여러 줄 내용 파싱 테스트"""
        output = """
        Thought: I need to search for information about Python.
        This is a complex query that might return multiple results.
        Action: web_search
        Action Input: {
            "query": "Python programming tutorial",
            "max_results": 5
        }
        """
        
        step = parse_react_output(output)
        assert "complex query" in step.thought
        assert step.action == "web_search"
        assert step.action_input["query"] == "Python programming tutorial"
        assert step.action_input["max_results"] == 5


class TestReactAgent:
    """ReactAgent 테스트"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM 생성"""
        llm = Mock()
        llm.model = "test-model"
        return llm
    
    @pytest.fixture
    def calculator_tool(self):
        """계산기 도구"""
        return Tool(
            name="calculator",
            description="Performs calculations",
            func=Calculator().run,
            args_schema=Calculator().args_schema
        )
    
    def test_agent_initialization(self, mock_llm, calculator_tool):
        """Agent 초기화 테스트"""
        agent = ReactAgent(
            llm=mock_llm,
            tools=[calculator_tool],
            max_iterations=5
        )
        
        assert agent.llm == mock_llm
        assert len(agent.tools) == 1
        assert agent.max_iterations == 5
        assert agent.get_tool("calculator") == calculator_tool
    
    def test_agent_single_step_execution(self, mock_llm, calculator_tool):
        """단일 단계 실행 테스트"""
        # LLM이 계산 요청을 반환하도록 설정
        mock_llm.ask.side_effect = [
            """
            Thought: I need to calculate 15 + 25
            Action: calculator
            Action Input: {"expression": "15 + 25"}
            """,
            """
            Thought: I have the result from the calculation
            Final Answer: The result of 15 + 25 is 40.
            """
        ]
        
        agent = ReactAgent(llm=mock_llm, tools=[calculator_tool])
        result = agent.run("What is 15 + 25?")
        
        assert result == "The result of 15 + 25 is 40."
        assert mock_llm.ask.call_count == 2
    
    def test_agent_with_invalid_action(self, mock_llm, calculator_tool):
        """잘못된 액션 처리 테스트"""
        mock_llm.ask.side_effect = [
            """
            Thought: I'll use a non-existent tool
            Action: nonexistent_tool
            Action Input: {"data": "test"}
            """,
            """
            Thought: The tool doesn't exist, let me use calculator instead
            Action: calculator
            Action Input: {"expression": "5 * 5"}
            """,
            """
            Thought: I have the answer
            Final Answer: The result is 25.
            """
        ]
        
        agent = ReactAgent(llm=mock_llm, tools=[calculator_tool])
        result = agent.run("Calculate something")
        
        assert result == "The result is 25."
        # 두 번째 호출에서 에러 메시지가 포함되었는지 확인 (history에 포함됨)
        # 모든 호출 확인
        assert mock_llm.ask.call_count == 3
        # history가 포함된 프롬프트에서 에러 메시지 확인
        second_call = str(mock_llm.ask.call_args_list[1][0][0])
        assert "not found" in second_call.lower() or "error" in second_call.lower()
    
    def test_agent_max_iterations(self, mock_llm, calculator_tool):
        """최대 반복 횟수 제한 테스트"""
        # 항상 새로운 액션을 시도하도록 설정
        mock_llm.ask.return_value = """
        Thought: I need to calculate something
        Action: calculator
        Action Input: {"expression": "1 + 1"}
        """
        
        agent = ReactAgent(llm=mock_llm, tools=[calculator_tool], max_iterations=3)
        result = agent.run("Keep calculating")
        
        assert "maximum iterations" in result.lower()
        assert mock_llm.ask.call_count == 3
    
    def test_agent_with_tool_validation_error(self, mock_llm, calculator_tool):
        """도구 검증 오류 처리 테스트"""
        mock_llm.ask.side_effect = [
            """
            Thought: I'll try an invalid expression
            Action: calculator
            Action Input: {"expression": "2 + 2; print('hack')"}
            """,
            """
            Thought: The input was invalid, let me fix it
            Action: calculator
            Action Input: {"expression": "2 + 2"}
            """,
            """
            Thought: Now I have the correct result
            Final Answer: The answer is 4.
            """
        ]
        
        agent = ReactAgent(llm=mock_llm, tools=[calculator_tool])
        result = agent.run("Calculate 2 + 2")
        
        assert result == "The answer is 4."
        # 검증 오류가 history에 포함되었는지 확인
        assert mock_llm.ask.call_count == 3
        # history가 포함된 프롬프트에서 검증 오류 확인
        second_call = str(mock_llm.ask.call_args_list[1][0][0])
        assert "validation" in second_call.lower() or "error" in second_call.lower()


class TestAsyncReactAgent:
    """비동기 ReactAgent 테스트"""
    
    @pytest.fixture
    def async_mock_llm(self):
        """비동기 Mock LLM 생성"""
        llm = AsyncMock()
        llm.model = "test-model"
        # ask 메서드도 설정
        llm.ask = Mock()
        return llm
    
    @pytest.fixture
    def calculator_tool(self):
        """계산기 도구"""
        return Tool(
            name="calculator",
            description="Performs calculations",
            func=Calculator().run,
            args_schema=Calculator().args_schema
        )
    
    @pytest.mark.asyncio
    async def test_async_agent_execution(self, async_mock_llm, calculator_tool):
        """비동기 Agent 실행 테스트"""
        # aask 메서드 설정
        async_mock_llm.aask.side_effect = [
            """
            Thought: I need to calculate 20 * 3
            Action: calculator
            Action Input: {"expression": "20 * 3"}
            """,
            """
            Thought: I have the result
            Final Answer: 20 multiplied by 3 equals 60.
            """
        ]
        
        agent = AsyncReactAgent(llm=async_mock_llm, tools=[calculator_tool])
        result = await agent.arun("What is 20 times 3?")
        
        assert result == "20 multiplied by 3 equals 60."
        assert async_mock_llm.aask.call_count == 2
    
    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """비동기 도구 실행 테스트"""
        # 비동기 도구 생성
        async def async_search(query: str) -> str:
            await asyncio.sleep(0.01)
            return f"Results for: {query}"
        
        search_tool = Tool(
            name="search",
            description="Search the web",
            func=async_search
        )
        
        mock_llm = AsyncMock()
        mock_llm.aask.side_effect = [
            """
            Thought: I'll search for Python
            Action: search
            Action Input: {"query": "Python tutorials"}
            """,
            """
            Thought: I found the results
            Final Answer: Found results for Python tutorials.
            """
        ]
        
        agent = AsyncReactAgent(llm=mock_llm, tools=[search_tool])
        result = await agent.arun("Search for Python tutorials")
        
        assert "Found results" in result


class TestCreateReactAgent:
    """create_react_agent 팩토리 함수 테스트"""
    
    def test_create_sync_agent(self):
        """동기 Agent 생성 테스트"""
        mock_llm = Mock()
        calc_tool = Tool(
            name="calc",
            description="Calculator",
            func=lambda x: str(eval(x))
        )
        
        agent = create_react_agent(mock_llm, [calc_tool])
        assert isinstance(agent, ReactAgent)
        assert not isinstance(agent, AsyncReactAgent)
    
    def test_create_async_agent(self):
        """비동기 Agent 생성 테스트"""
        mock_llm = Mock()
        
        async def async_func(x):
            return x
        
        async_tool = Tool(
            name="async_tool",
            description="Async tool",
            func=async_func
        )
        
        # 비동기 도구가 있으면 AsyncReactAgent 생성
        agent = create_react_agent(mock_llm, [async_tool])
        assert isinstance(agent, AsyncReactAgent)
    
    def test_create_agent_with_options(self):
        """옵션을 사용한 Agent 생성 테스트"""
        mock_llm = Mock()
        tool = Tool(name="test", description="Test", func=lambda: "test")
        
        agent = create_react_agent(
            mock_llm,
            [tool],
            max_iterations=20,
            timeout=30
        )
        
        assert agent.max_iterations == 20
        assert agent.timeout == 30