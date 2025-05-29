"""Tests for pyhub.llm.agents module."""

import asyncio
import json
import pytest
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch

from pydantic import BaseModel, Field, validator

from pyhub.llm.agents.base import Tool, BaseTool, AsyncBaseTool, ValidationLevel
from pyhub.llm.agents.tools import Calculator, CalculatorInput


class TestTool:
    """Tool 클래스 테스트"""
    
    def test_tool_creation(self):
        """기본 Tool 생성 테스트"""
        def sample_func(x: int) -> str:
            return str(x * 2)
        
        tool = Tool(
            name="multiplier",
            description="Multiply by 2",
            func=sample_func
        )
        
        assert tool.name == "multiplier"
        assert tool.description == "Multiply by 2"
        assert tool.func(5) == "10"
        assert tool.is_async is False
    
    def test_async_tool_detection(self):
        """비동기 함수 자동 감지 테스트"""
        async def async_func(x: int) -> str:
            await asyncio.sleep(0.01)
            return str(x * 2)
        
        tool = Tool(
            name="async_multiplier",
            description="Async multiply by 2",
            func=async_func
        )
        
        assert tool.is_async is True
    
    def test_tool_validation_with_schema(self):
        """Pydantic 스키마를 사용한 검증 테스트"""
        class MultiplyInput(BaseModel):
            value: int = Field(..., ge=0, le=100)
            factor: int = Field(default=2, ge=1, le=10)
        
        def multiply(value: int, factor: int = 2) -> str:
            return str(value * factor)
        
        tool = Tool(
            name="multiply",
            description="Multiply values",
            func=multiply,
            args_schema=MultiplyInput,
            validation_level=ValidationLevel.STRICT
        )
        
        # 유효한 입력
        is_valid, error = tool.validate_input(value=10, factor=3)
        assert is_valid is True
        assert error is None
        
        # 유효하지 않은 입력 (value > 100)
        is_valid, error = tool.validate_input(value=150, factor=2)
        assert is_valid is False
        assert "validation error" in error.lower()
        
        # 유효하지 않은 입력 (음수)
        is_valid, error = tool.validate_input(value=-5, factor=2)
        assert is_valid is False
        assert error is not None
    
    def test_tool_custom_validators(self):
        """커스텀 검증 함수 테스트"""
        def is_even(value: int, **kwargs) -> Tuple[bool, Optional[str]]:
            if value % 2 != 0:
                return False, "Value must be even"
            return True, None
        
        def max_result_check(value: int, factor: int = 2, **kwargs) -> Tuple[bool, Optional[str]]:
            if value * factor > 200:
                return False, "Result would be too large"
            return True, None
        
        tool = Tool(
            name="even_multiply",
            description="Multiply even numbers",
            func=lambda value, factor=2: str(value * factor),
            pre_validators=[is_even, max_result_check]
        )
        
        # 유효한 입력 (짝수, 결과 < 200)
        is_valid, error = tool.validate_input(value=10, factor=5)
        assert is_valid is True
        
        # 홀수 입력
        is_valid, error = tool.validate_input(value=11, factor=5)
        assert is_valid is False
        assert "must be even" in error
        
        # 결과가 너무 큰 경우
        is_valid, error = tool.validate_input(value=50, factor=5)
        assert is_valid is False
        assert "too large" in error
    
    def test_validation_levels(self):
        """검증 레벨 테스트"""
        class StrictInput(BaseModel):
            value: int = Field(..., ge=0)
        
        # STRICT 레벨
        strict_tool = Tool(
            name="strict",
            description="Strict validation",
            func=lambda value: str(value),
            args_schema=StrictInput,
            validation_level=ValidationLevel.STRICT
        )
        
        is_valid, error = strict_tool.validate_input(value=-1)
        assert is_valid is False
        
        # WARNING 레벨
        warning_tool = Tool(
            name="warning",
            description="Warning validation",
            func=lambda value: str(value),
            args_schema=StrictInput,
            validation_level=ValidationLevel.WARNING
        )
        
        # WARNING 레벨에서는 검증 실패해도 True 반환
        with patch('logging.Logger.warning') as mock_warning:
            is_valid, error = warning_tool.validate_input(value=-1)
            assert is_valid is True
            assert error is None
            mock_warning.assert_called()
        
        # NONE 레벨
        none_tool = Tool(
            name="none",
            description="No validation",
            func=lambda value: str(value),
            args_schema=StrictInput,
            validation_level=ValidationLevel.NONE
        )
        
        is_valid, error = none_tool.validate_input(value=-1)
        assert is_valid is True


class TestCalculator:
    """Calculator 도구 테스트"""
    
    def test_calculator_input_validation(self):
        """계산기 입력 검증 테스트"""
        # 유효한 수식
        valid_expressions = [
            "2 + 2",
            "10 * (5 + 3)",
            "3.14 * 2",
            "(1 + 2) * (3 + 4)",
            "100 / 5 - 10"
        ]
        
        for expr in valid_expressions:
            input_model = CalculatorInput(expression=expr)
            assert input_model.expression == expr
        
        # 유효하지 않은 수식
        invalid_expressions = [
            "2 + 2; print('hack')",  # 보안 위험
            "import os",  # 모듈 임포트
            "__import__('os')",  # 동적 임포트
            "2 ** 1000000",  # 너무 큰 연산
            "eval('2+2')",  # eval 사용
            "2 + ",  # 불완전한 수식
        ]
        
        for expr in invalid_expressions:
            with pytest.raises(ValueError):
                CalculatorInput(expression=expr)
    
    def test_calculator_execution(self):
        """계산기 실행 테스트"""
        calc = Calculator()
        
        # 기본 연산
        assert calc.run("2 + 2") == "4"
        assert calc.run("10 * 5") == "50"
        assert calc.run("100 / 4") == "25"  # 정수로 표현 가능한 경우
        assert calc.run("10 / 3") == "3.333333"  # 소수점이 필요한 경우
        assert calc.run("2 ** 3") == "8"
        
        # 복잡한 연산
        assert calc.run("(10 + 5) * 2") == "30"
        assert calc.run("3.14 * 2") == "6.28"
    
    def test_calculator_with_tool_validation(self):
        """Tool 검증 시스템과 통합 테스트"""
        calc = Calculator()
        
        # Tool 객체로 변환
        tool = Tool(
            name=calc.name,
            description=calc.description,
            func=calc.run,
            args_schema=calc.args_schema
        )
        
        # 유효한 입력
        is_valid, error = tool.validate_input(expression="5 + 5")
        assert is_valid is True
        assert tool.func(**{"expression": "5 + 5"}) == "10"
        
        # 유효하지 않은 입력
        is_valid, error = tool.validate_input(expression="__import__('os')")
        assert is_valid is False
        assert "invalid" in error.lower()


class TestAsyncTools:
    """비동기 도구 테스트"""
    
    @pytest.mark.asyncio
    async def test_async_tool_execution(self):
        """비동기 도구 실행 테스트"""
        class AsyncCounter(AsyncBaseTool):
            def __init__(self):
                self.count = 0
                super().__init__(
                    name="async_counter",
                    description="Async counter"
                )
            
            async def arun(self, increment: int = 1) -> str:
                await asyncio.sleep(0.01)  # 비동기 작업 시뮬레이션
                self.count += increment
                return str(self.count)
        
        counter = AsyncCounter()
        
        # 비동기 실행
        result1 = await counter.arun(increment=5)
        assert result1 == "5"
        
        result2 = await counter.arun(increment=3)
        assert result2 == "8"
    
    @pytest.mark.asyncio
    async def test_tool_executor(self):
        """ToolExecutor 테스트"""
        from pyhub.llm.agents.base import ToolExecutor
        
        # 동기 도구
        sync_tool = Tool(
            name="sync",
            description="Sync tool",
            func=lambda x: f"sync: {x}"
        )
        
        # 비동기 도구
        async def async_func(x):
            await asyncio.sleep(0.01)
            return f"async: {x}"
        
        async_tool = Tool(
            name="async",
            description="Async tool",
            func=async_func
        )
        
        # 동기 도구를 동기/비동기로 실행
        sync_result = ToolExecutor.execute_tool(sync_tool, "test")
        assert sync_result == "sync: test"
        
        async_sync_result = await ToolExecutor.aexecute_tool(sync_tool, "test")
        assert async_sync_result == "sync: test"
        
        # 비동기 도구를 동기로 실행 - async 컨텍스트에서는 에러
        with pytest.raises(RuntimeError) as exc_info:
            ToolExecutor.execute_tool(async_tool, "test")
        assert "Cannot execute async tool" in str(exc_info.value)
        
        async_result = await ToolExecutor.aexecute_tool(async_tool, "test")
        assert async_result == "async: test"


class TestToolWithRealWorldScenarios:
    """실제 시나리오 기반 도구 테스트"""
    
    def test_file_operation_security(self):
        """파일 작업 보안 검증 테스트"""
        from pyhub.llm.agents.tools import FileOperationInput
        
        # 안전한 경로
        safe_paths = [
            "data.txt",
            "./logs/app.log",
            "output/result.json"
        ]
        
        for path in safe_paths:
            input_model = FileOperationInput(
                path=path,
                operation="read"
            )
            assert input_model.path == path
        
        # 위험한 경로
        unsafe_paths = [
            "../../../etc/passwd",  # 경로 탐색
            "/etc/shadow",  # 시스템 파일
            "/sys/power/state",  # 시스템 제어
        ]
        
        for path in unsafe_paths:
            with pytest.raises(ValueError) as exc_info:
                FileOperationInput(path=path, operation="read")
            error_msg = str(exc_info.value).lower()
            # 경로 탐색이나 접근 금지 관련 메시지 확인
            assert any(word in error_msg for word in ["traversal", "not allowed", "access"])
    
    def test_web_search_validation(self):
        """웹 검색 입력 검증 테스트"""
        from pyhub.llm.agents.tools import WebSearchInput
        
        # 유효한 검색
        valid_search = WebSearchInput(
            query="Python tutorial",
            max_results=10,
            language="en"
        )
        assert valid_search.query == "Python tutorial"
        assert valid_search.max_results == 10
        
        # 너무 긴 쿼리
        with pytest.raises(ValueError):
            WebSearchInput(query="a" * 201)  # 200자 제한 초과
        
        # 잘못된 결과 수
        with pytest.raises(ValueError):
            WebSearchInput(query="test", max_results=0)
        
        with pytest.raises(ValueError):
            WebSearchInput(query="test", max_results=21)  # 20개 제한
        
        # 잘못된 언어 코드
        with pytest.raises(ValueError):
            WebSearchInput(query="test", language="english")  # 2자리 코드여야 함