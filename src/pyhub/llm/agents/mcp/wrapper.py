"""MCP tool wrapper for pyhub agents."""

import logging
from typing import Any, Dict, Type

from pydantic import BaseModel, Field, create_model

from ..base import AsyncBaseTool, ValidationLevel
from .client import MCPClient

logger = logging.getLogger(__name__)


def create_pydantic_schema(parameters: Dict[str, Any]) -> Type[BaseModel]:
    """MCP 파라미터 정의에서 Pydantic 스키마 생성"""

    if not parameters:
        # 파라미터가 없는 경우 빈 모델 반환
        return create_model("EmptySchema")

    # JSON Schema를 Pydantic 필드로 변환
    fields = {}

    # properties가 있는 경우 (JSON Schema 형식)
    properties = parameters.get("properties", {})
    required = parameters.get("required", [])

    for prop_name, prop_def in properties.items():
        # 타입 매핑
        python_type = Any
        if "type" in prop_def:
            type_map = {
                "string": str,
                "number": float,
                "integer": int,
                "boolean": bool,
                "array": list,
                "object": dict,
            }
            python_type = type_map.get(prop_def["type"], Any)

        # 기본값 설정
        default = ... if prop_name in required else None

        # 설명 추출
        description = prop_def.get("description", f"Parameter: {prop_name}")

        # 필드 생성
        fields[prop_name] = (python_type, Field(default, description=description))

    # 동적 모델 생성
    model_name = "MCPToolSchema"
    return create_model(model_name, **fields)


class MCPTool(AsyncBaseTool):
    """MCP 도구를 pyhub AsyncBaseTool로 래핑"""

    def __init__(self, tool_def: Dict[str, Any], client: MCPClient):
        """
        Args:
            tool_def: MCP 도구 정의
            client: MCP 클라이언트
        """
        self.client = client
        self.mcp_name = tool_def["name"]

        # 부모 클래스 초기화
        super().__init__(name=tool_def["name"], description=tool_def.get("description", "MCP tool"))

        # 파라미터 스키마 생성
        parameters = tool_def.get("parameters", {})
        self.args_schema = create_pydantic_schema(parameters)

        # MCP 도구는 일반적으로 외부 호출이므로 WARNING 레벨 사용
        self.validation_level = ValidationLevel.WARNING

        logger.debug(f"Created MCPTool wrapper for '{self.mcp_name}'")

    async def arun(self, **kwargs) -> str:
        """비동기로 MCP 도구 실행"""
        try:
            # MCP 클라이언트를 통해 도구 실행
            result = await self.client.execute_tool(self.mcp_name, kwargs)
            return result
        except Exception as e:
            logger.error(f"Error running MCP tool '{self.mcp_name}': {e}")
            return f"Error executing MCP tool: {str(e)}"

    def run(self, **kwargs) -> str:
        """동기 실행 (비동기를 동기로 변환)"""
        import asyncio

        # 이미 이벤트 루프가 실행 중인지 확인
        try:
            loop = asyncio.get_running_loop()
            # 이미 루프가 실행 중이면 에러
            raise RuntimeError(
                f"MCPTool '{self.name}' requires async execution. " "Use 'await arun()' or AsyncReactAgent instead."
            )
        except RuntimeError:
            # 루프가 없으면 새로 생성하여 실행
            return asyncio.run(self.arun(**kwargs))
