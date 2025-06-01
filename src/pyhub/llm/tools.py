"""
Function Calling and Tool Integration for pyhub.llm

이 모듈은 다양한 형태의 도구들을 통합하여 LLM에서 직접 사용할 수 있도록 합니다.
기존 Agent 시스템과 호환되면서 새로운 함수 기반 도구도 지원합니다.
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Type, get_type_hints

from pydantic import BaseModel, Field, create_model

from .agents.base import AsyncBaseTool, BaseTool, Tool, ValidationLevel
from .agents.mcp.wrapper import MCPTool

logger = logging.getLogger(__name__)


class FunctionToolAdapter:
    """일반 함수를 Tool 객체로 변환하는 어댑터"""

    @staticmethod
    def extract_function_schema(func: Callable) -> Dict[str, Any]:
        """함수에서 스키마 정보를 추출합니다."""
        # 함수가 callable 객체인지 확인
        if hasattr(func, "__call__") and not inspect.isfunction(func):
            # Callable 객체의 경우 __call__ 메서드 사용
            actual_func = func.__call__
            name = func.__class__.__name__
            description = func.__class__.__doc__ or func.__call__.__doc__ or ""
        else:
            # 일반 함수의 경우
            actual_func = func
            name = func.__name__
            description = func.__doc__ or ""

        # 함수 시그니처 분석
        signature = inspect.signature(actual_func)
        type_hints = get_type_hints(actual_func)

        parameters = {}
        required_params = []

        for param_name, param in signature.parameters.items():
            if param_name == "self":  # __call__ 메서드의 self 제외
                continue

            param_type = type_hints.get(param_name, str)
            json_type = FunctionToolAdapter._python_type_to_json_schema_type(param_type)

            param_info = {"type": json_type, "description": f"Parameter: {param_name}"}

            if param.default != inspect.Parameter.empty:
                param_info["default"] = param.default
            else:
                required_params.append(param_name)

            parameters[param_name] = param_info

        return {
            "name": name,
            "description": description.strip(),
            "parameters": {"type": "object", "properties": parameters, "required": required_params},
            "callable": func,
            "is_async": asyncio.iscoroutinefunction(actual_func),
        }

    @staticmethod
    def _python_type_to_json_schema_type(python_type: Type) -> str:
        """Python 타입을 JSON Schema 타입으로 변환"""
        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        # typing 모듈의 제네릭 타입 처리
        origin = getattr(python_type, "__origin__", None)
        if origin is not None:
            return type_mapping.get(origin, "string")

        return type_mapping.get(python_type, "string")

    @staticmethod
    def create_pydantic_schema_from_function(func: Callable) -> Type[BaseModel]:
        """함수에서 Pydantic 스키마를 생성합니다."""
        schema = FunctionToolAdapter.extract_function_schema(func)
        properties = schema["parameters"]["properties"]
        required = schema["parameters"]["required"]

        if not properties:
            return create_model("EmptySchema")

        fields = {}
        for prop_name, prop_def in properties.items():
            # JSON Schema 타입을 Python 타입으로 변환
            python_type = {
                "string": str,
                "integer": int,
                "number": float,
                "boolean": bool,
                "array": list,
                "object": dict,
            }.get(prop_def["type"], str)

            default = ... if prop_name in required else prop_def.get("default")
            description = prop_def.get("description", f"Parameter: {prop_name}")

            fields[prop_name] = (python_type, Field(default, description=description))

        model_name = f"{schema['name']}Schema"
        return create_model(model_name, **fields)

    @staticmethod
    def create_tool_from_function(func: Callable) -> Tool:
        """함수를 Tool 객체로 변환합니다."""
        schema = FunctionToolAdapter.extract_function_schema(func)
        pydantic_schema = FunctionToolAdapter.create_pydantic_schema_from_function(func)

        return Tool(
            name=schema["name"],
            description=schema["description"],
            func=schema["callable"],
            args_schema=pydantic_schema,
            validation_level=ValidationLevel.STRICT,
        )


class ToolAdapter:
    """다양한 도구 형태를 통합 Tool 객체로 변환하는 어댑터"""

    @staticmethod
    def adapt_tool(tool_input: Any) -> Tool:
        """모든 형태의 도구를 Tool 객체로 변환합니다."""

        # 1. 이미 Tool 객체인 경우
        if isinstance(tool_input, Tool):
            return tool_input

        # 2. BaseTool 인스턴스 (동기)
        elif isinstance(tool_input, BaseTool):
            return Tool(
                name=tool_input.name,
                description=tool_input.description,
                func=tool_input.run,
                args_schema=tool_input.args_schema,
                validation_level=getattr(tool_input, "validation_level", ValidationLevel.STRICT),
            )

        # 3. AsyncBaseTool 인스턴스 (비동기)
        elif isinstance(tool_input, AsyncBaseTool):
            return Tool(
                name=tool_input.name,
                description=tool_input.description,
                func=tool_input.arun,
                args_schema=tool_input.args_schema,
                validation_level=getattr(tool_input, "validation_level", ValidationLevel.STRICT),
            )

        # 4. MCPTool 인스턴스
        elif isinstance(tool_input, MCPTool):
            return Tool(
                name=tool_input.name,
                description=tool_input.description,
                func=tool_input.arun,
                args_schema=tool_input.args_schema,
                validation_level=tool_input.validation_level,
            )

        # 5. 일반 함수 또는 callable 객체
        elif callable(tool_input):
            return FunctionToolAdapter.create_tool_from_function(tool_input)

        else:
            raise ValueError(f"Unsupported tool type: {type(tool_input)}")

    @staticmethod
    def adapt_tools(tool_inputs: List[Any]) -> List[Tool]:
        """도구 리스트를 모두 Tool 객체로 변환합니다."""
        return [ToolAdapter.adapt_tool(tool) for tool in tool_inputs]


class ProviderToolConverter:
    """Provider별 도구 스키마 변환기"""

    @staticmethod
    def to_openai_function(tool: Tool) -> Dict[str, Any]:
        """OpenAI Function Calling 형식으로 변환"""
        # Agent Tool의 경우 args_schema를 직접 사용
        if hasattr(tool, "args_schema") and tool.args_schema:
            try:
                # Pydantic 모델의 JSON schema 추출

                pydantic_schema = tool.args_schema.model_json_schema()

                # OpenAI Function Calling 형식으로 변환
                return {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": pydantic_schema.get("properties", {}),
                            "required": pydantic_schema.get("required", []),
                        },
                    },
                }
            except Exception:
                # Pydantic 스키마 추출 실패 시 fallback
                pass

        # 일반 함수 또는 fallback의 경우 기존 방식 사용
        schema = FunctionToolAdapter.extract_function_schema(tool.func)

        return {
            "type": "function",
            "function": {"name": tool.name, "description": tool.description, "parameters": schema["parameters"]},
        }

    @staticmethod
    def to_anthropic_tool(tool: Tool) -> Dict[str, Any]:
        """Anthropic Tool Use 형식으로 변환"""
        schema = FunctionToolAdapter.extract_function_schema(tool.func)

        return {"name": tool.name, "description": tool.description, "input_schema": schema["parameters"]}

    @staticmethod
    def to_google_function(tool: Tool) -> Dict[str, Any]:
        """Google Function Calling 형식으로 변환"""
        schema = FunctionToolAdapter.extract_function_schema(tool.func)

        return {"name": tool.name, "description": tool.description, "parameters": schema["parameters"]}


class ToolExecutor:
    """도구 실행을 관리하는 통합 실행기"""

    def __init__(self, tools: List[Tool]):
        self.tools = {tool.name: tool for tool in tools}

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """도구를 실행하고 결과를 반환합니다."""
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found"

        tool = self.tools[tool_name]

        try:
            # 입력값 검증
            is_valid, error_message = tool.validate_input(**arguments)
            if not is_valid:
                return f"Validation error for {tool_name}: {error_message}"

            # 도구 실행
            if tool.is_async:
                # 비동기 도구의 경우
                try:
                    loop = asyncio.get_running_loop()
                    # 이미 이벤트 루프가 실행 중이면 에러
                    return f"Error: Cannot execute async tool '{tool_name}' in sync context"
                except RuntimeError:
                    # 이벤트 루프가 없으면 새로 생성하여 실행
                    result = asyncio.run(tool.func(**arguments))
            else:
                # 동기 도구의 경우
                result = tool.func(**arguments)

            return str(result)

        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return f"Error executing {tool_name}: {str(e)}"

    async def execute_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """비동기로 도구를 실행합니다."""
        if tool_name not in self.tools:
            return f"Error: Tool '{tool_name}' not found"

        tool = self.tools[tool_name]

        try:
            # 입력값 검증
            is_valid, error_message = tool.validate_input(**arguments)
            if not is_valid:
                return f"Validation error for {tool_name}: {error_message}"

            # 도구 실행
            if tool.is_async:
                result = await tool.func(**arguments)
            else:
                # 동기 도구를 비동기로 실행
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: tool.func(**arguments))

            return str(result)

        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return f"Error executing {tool_name}: {str(e)}"


# 편의 함수들
def create_tool_from_function(func: Callable) -> Tool:
    """함수를 Tool 객체로 변환하는 편의 함수"""
    return FunctionToolAdapter.create_tool_from_function(func)


def adapt_tools(*tools) -> List[Tool]:
    """여러 도구를 Tool 객체 리스트로 변환하는 편의 함수"""
    return ToolAdapter.adapt_tools(list(tools))


__all__ = [
    "ToolAdapter",
    "FunctionToolAdapter",
    "ProviderToolConverter",
    "ToolExecutor",
    "create_tool_from_function",
    "adapt_tools",
]
