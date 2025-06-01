"""Tests for MCP integration."""

from unittest.mock import AsyncMock, Mock

import pytest

from pyhub.llm.agents.mcp import MCPClient, MCPTool, load_mcp_tools
from pyhub.llm.agents.mcp.wrapper import create_pydantic_schema


class TestMCPSchemaConversion:
    """MCP 스키마 변환 테스트"""

    def test_create_empty_schema(self):
        """빈 파라미터 스키마 생성"""
        schema = create_pydantic_schema({})
        assert schema.__name__ == "EmptySchema"
        assert len(schema.model_fields) == 0

    def test_create_simple_schema(self):
        """간단한 스키마 생성"""
        parameters = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Your name"},
                "age": {"type": "integer", "description": "Your age"},
            },
            "required": ["name"],
        }

        schema = create_pydantic_schema(parameters)

        # 필드 확인
        assert "name" in schema.model_fields
        assert "age" in schema.model_fields

        # 타입 확인
        assert schema.model_fields["name"].annotation == str
        assert schema.model_fields["age"].annotation == int

        # 필수 필드 확인
        assert schema.model_fields["name"].is_required()
        assert not schema.model_fields["age"].is_required()

    def test_create_complex_schema(self):
        """복잡한 스키마 생성"""
        parameters = {
            "type": "object",
            "properties": {
                "numbers": {"type": "array", "description": "List of numbers"},
                "config": {"type": "object", "description": "Configuration"},
                "enabled": {"type": "boolean", "description": "Is enabled"},
            },
            "required": ["numbers", "enabled"],
        }

        schema = create_pydantic_schema(parameters)

        # 타입 확인
        assert schema.model_fields["numbers"].annotation == list
        assert schema.model_fields["config"].annotation == dict
        assert schema.model_fields["enabled"].annotation == bool


class TestMCPTool:
    """MCPTool 래퍼 테스트"""

    def test_mcp_tool_creation(self):
        """MCPTool 생성 테스트"""
        tool_def = {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {"type": "object", "properties": {"input": {"type": "string"}}, "required": ["input"]},
        }

        mock_client = Mock(spec=MCPClient)
        tool = MCPTool(tool_def, mock_client)

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.args_schema is not None
        assert "input" in tool.args_schema.model_fields

    @pytest.mark.asyncio
    async def test_mcp_tool_execution(self):
        """MCPTool 실행 테스트"""
        tool_def = {"name": "calculator", "description": "Calculate expression"}

        mock_client = AsyncMock(spec=MCPClient)
        mock_client.execute_tool.return_value = "42"

        tool = MCPTool(tool_def, mock_client)
        result = await tool.arun(expression="21 * 2")

        assert result == "42"
        mock_client.execute_tool.assert_called_once_with("calculator", {"expression": "21 * 2"})


class TestMCPLoader:
    """MCP 도구 로더 테스트"""

    @pytest.mark.asyncio
    async def test_load_mcp_tools(self):
        """MCP 도구 로드 테스트"""
        # Mock MCP 클라이언트
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.list_tools.return_value = [
            {
                "name": "add",
                "description": "Add two numbers",
                "parameters": {
                    "type": "object",
                    "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                    "required": ["a", "b"],
                },
            },
            {"name": "multiply", "description": "Multiply two numbers", "parameters": {}},
        ]

        # 도구 로드
        tools = await load_mcp_tools(mock_client)

        assert len(tools) == 2
        assert tools[0].name == "add"
        assert tools[0].description == "Add two numbers"
        assert tools[1].name == "multiply"
        assert tools[1].description == "Multiply two numbers"

    @pytest.mark.asyncio
    async def test_load_mcp_tools_with_filter(self):
        """필터를 사용한 MCP 도구 로드 테스트"""
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.list_tools.return_value = [
            {"name": "tool1", "description": "Tool 1"},
            {"name": "tool2", "description": "Tool 2"},
            {"name": "tool3", "description": "Tool 3"},
        ]

        # 특정 도구만 로드
        tools = await load_mcp_tools(mock_client, filter_tools=["tool1", "tool3"])

        assert len(tools) == 2
        assert tools[0].name == "tool1"
        assert tools[1].name == "tool3"


class TestMCPClient:
    """MCPClient 테스트"""

    @pytest.mark.asyncio
    async def test_mcp_client_list_tools(self):
        """도구 목록 가져오기 테스트"""
        # Mock MCP 세션
        mock_session = AsyncMock()
        # Mock 객체의 속성을 명시적으로 설정
        tool1 = Mock()
        tool1.name = "tool1"
        tool1.description = "Tool 1"
        tool1.inputSchema = {"type": "object"}

        tool2 = Mock()
        tool2.name = "tool2"
        tool2.description = "Tool 2"

        mock_session.list_tools.return_value = Mock(tools=[tool1, tool2])

        client = MCPClient(None)
        client._session = mock_session

        tools = await client.list_tools()

        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"
        assert tools[0]["description"] == "Tool 1"
        assert tools[1]["name"] == "tool2"
        assert tools[1]["description"] == "Tool 2"

    @pytest.mark.asyncio
    async def test_mcp_client_execute_tool(self):
        """도구 실행 테스트"""
        # Mock MCP 세션
        mock_session = AsyncMock()
        mock_result = Mock(content=[Mock(text="Result: 42")])
        mock_session.call_tool.return_value = mock_result

        client = MCPClient(None)
        client._session = mock_session

        result = await client.execute_tool("calculator", {"expression": "21 * 2"})

        assert result == "Result: 42"
        mock_session.call_tool.assert_called_once_with("calculator", {"expression": "21 * 2"})
