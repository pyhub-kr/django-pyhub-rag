"""Base classes for agent system."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, List, Optional, Tuple, Type, Union

from asgiref.sync import async_to_sync
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """검증 레벨"""

    STRICT = "strict"  # 모든 검증 실패 시 도구 실행 안함
    WARNING = "warning"  # 검증 실패 시 경고만 하고 실행
    NONE = "none"  # 검증 없이 실행


@dataclass
class Tool:
    """도구 정의"""

    name: str
    description: str
    func: Union[Callable[..., str], Callable[..., Awaitable[str]]]
    args_schema: Optional[Type[BaseModel]] = None
    validation_level: ValidationLevel = ValidationLevel.STRICT
    pre_validators: List[Callable] = field(default_factory=list)
    is_async: bool = field(init=False)

    def __post_init__(self):
        """비동기 함수 자동 감지"""
        if asyncio.iscoroutinefunction(self.func):
            self.is_async = True
        else:
            self.is_async = False

    def validate_input(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """입력값 검증"""
        # NONE 레벨은 검증 건너뜀
        if self.validation_level == ValidationLevel.NONE:
            return True, None

        # 1. 스키마 검증 (Pydantic)
        if self.args_schema:
            try:
                validated_args = self.args_schema(**kwargs)
                # 검증된 값으로 kwargs 업데이트
                kwargs.update(validated_args.dict())
            except ValidationError as e:
                error_msg = f"Validation error: {e}"
                if self.validation_level == ValidationLevel.STRICT:
                    return False, error_msg
                elif self.validation_level == ValidationLevel.WARNING:
                    logger.warning(f"Validation warning for {self.name}: {e}")

        # 2. 커스텀 검증
        for validator in self.pre_validators:
            try:
                is_valid, message = validator(**kwargs)
                if not is_valid:
                    if self.validation_level == ValidationLevel.STRICT:
                        return False, message
                    elif self.validation_level == ValidationLevel.WARNING:
                        logger.warning(f"Validation warning for {self.name}: {message}")
            except Exception as e:
                return False, f"Validator error: {e}"

        return True, None


class BaseTool(ABC):
    """동기 도구 기본 클래스"""

    def __init__(self, name: str, description: str, args_schema: Optional[Type[BaseModel]] = None):
        self.name = name
        self.description = description
        self.args_schema = args_schema

    @abstractmethod
    def run(self, *args, **kwargs) -> str:
        """도구 실행"""
        pass


class AsyncBaseTool(ABC):
    """비동기 도구 기본 클래스"""

    def __init__(self, name: str, description: str, args_schema: Optional[Type[BaseModel]] = None):
        self.name = name
        self.description = description
        self.args_schema = args_schema

    @abstractmethod
    async def arun(self, *args, **kwargs) -> str:
        """비동기 도구 실행"""
        pass


class ToolExecutor:
    """도구 실행을 관리하는 클래스"""

    @staticmethod
    def execute_tool(tool: Tool, *args, **kwargs) -> str:
        """동기 도구 실행"""
        if tool.is_async:
            # 이미 실행 중인 이벤트 루프가 있는지 확인
            try:
                loop = asyncio.get_running_loop()
                # 이미 async 컨텍스트에 있으면 에러
                raise RuntimeError(
                    f"Cannot execute async tool '{tool.name}' synchronously from async context. "
                    "Use aexecute_tool instead."
                )
            except RuntimeError as e:
                # "no running event loop" 에러인 경우에만 새로 실행
                if "no running event loop" in str(e):
                    return async_to_sync(tool.func)(*args, **kwargs)
                else:
                    # 다른 RuntimeError는 그대로 전파
                    raise
        return tool.func(*args, **kwargs)

    @staticmethod
    async def aexecute_tool(tool: Tool, *args, **kwargs) -> str:
        """비동기 도구 실행"""
        if tool.is_async:
            return await tool.func(*args, **kwargs)
        # 동기 도구를 비동기로 실행
        loop = asyncio.get_event_loop()
        if args:
            # args가 있으면 partial을 사용
            from functools import partial

            return await loop.run_in_executor(None, partial(tool.func, *args, **kwargs))
        else:
            # kwargs만 있으면 lambda 사용
            return await loop.run_in_executor(None, lambda: tool.func(**kwargs))


class BaseAgent(ABC):
    """동기 Agent 기본 클래스"""

    def __init__(self, llm: Any, tools: List[Tool], **kwargs):
        self.llm = llm
        self.tools = tools
        self.max_iterations = kwargs.get("max_iterations", 10)
        self.timeout = kwargs.get("timeout", None)
        self._tool_map = {tool.name: tool for tool in tools}

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """도구 이름으로 도구 가져오기"""
        return self._tool_map.get(tool_name)

    @abstractmethod
    def run(self, input: str) -> str:
        """Agent 실행"""
        pass


class AsyncBaseAgent(ABC):
    """비동기 Agent 기본 클래스"""

    def __init__(self, llm: Any, tools: List[Tool], **kwargs):
        self.llm = llm
        self.tools = tools
        self.max_iterations = kwargs.get("max_iterations", 10)
        self.timeout = kwargs.get("timeout", None)
        self._tool_map = {tool.name: tool for tool in tools}

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """도구 이름으로 도구 가져오기"""
        return self._tool_map.get(tool_name)

    @abstractmethod
    async def arun(self, input: str) -> str:
        """비동기 Agent 실행"""
        pass
