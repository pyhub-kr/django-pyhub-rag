"""Tool registry for managing available tools."""

from typing import Dict, List, Optional, Type

from ..base import BaseTool, Tool
from .calculator import Calculator
from .file_reader import FileReader
from .web_search import WebSearch


class ToolRegistry:
    """도구 레지스트리"""

    _instance = None
    _tools: Dict[str, Type[BaseTool]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_default_tools()
        return cls._instance

    def _initialize_default_tools(self):
        """기본 도구 등록"""
        self.register(Calculator)
        self.register(WebSearch)
        self.register(FileReader)

    def register(self, tool_class: Type[BaseTool]) -> None:
        """도구 클래스 등록"""
        instance = tool_class()
        self._tools[instance.name] = tool_class

    def get(self, name: str) -> Optional[Type[BaseTool]]:
        """이름으로 도구 클래스 가져오기"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, any]]:
        """모든 도구 정보 반환"""
        tools = []
        for tool_class in self._tools.values():
            instance = tool_class()
            tool_info = {"name": instance.name, "description": instance.description, "args": {}}

            # args_schema가 있으면 필드 정보 추출
            if hasattr(instance, "args_schema") and instance.args_schema:
                schema = instance.args_schema
                if hasattr(schema, "model_fields"):  # Pydantic v2
                    for field_name, field_info in schema.model_fields.items():
                        tool_info["args"][field_name] = field_info.description or f"Field: {field_name}"

            tools.append(tool_info)

        return tools

    def create_tool(self, name: str) -> Optional[Tool]:
        """도구 인스턴스 생성"""
        tool_class = self.get(name)
        if tool_class:
            instance = tool_class()
            return Tool(
                name=instance.name,
                description=instance.description,
                func=instance.run if hasattr(instance, "run") else instance.arun,
                args_schema=getattr(instance, "args_schema", None),
                validation_level=getattr(instance, "validation_level", None),
                pre_validators=getattr(instance, "pre_validators", []),
            )
        return None


# 싱글톤 인스턴스
tool_registry = ToolRegistry()
