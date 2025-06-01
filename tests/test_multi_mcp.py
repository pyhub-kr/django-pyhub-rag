"""Tests for Multi-server MCP integration."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pyhub.llm.agents.mcp import (
    MultiServerMCPClient,
    create_multi_server_client_from_config,
)


class TestMultiServerMCPClient:
    """MultiServerMCPClient 테스트"""

    @pytest.mark.asyncio
    async def test_multi_server_initialization(self):
        """다중 서버 초기화 테스트"""
        servers = {
            "math": {"command": "python", "args": ["math_server.py"]},
            "weather": {"command": "python", "args": ["weather_server.py"]},
        }

        client = MultiServerMCPClient(servers)

        assert client.servers == servers
        assert client.prefix_tools == False
        assert len(client._clients) == 0

    @pytest.mark.asyncio
    async def test_multi_server_with_prefix(self):
        """prefix 옵션 테스트"""
        servers = {"test": {"command": "test"}}
        client = MultiServerMCPClient(servers, prefix_tools=True)

        assert client.prefix_tools == True

    @pytest.mark.asyncio
    async def test_get_tools_with_multiple_servers(self):
        """여러 서버에서 도구 가져오기 테스트"""
        # Mock 도구 정의
        add_tool = Mock()
        add_tool.name = "add"
        add_tool.description = "Add numbers"

        multiply_tool = Mock()
        multiply_tool.name = "multiply"
        multiply_tool.description = "Multiply numbers"

        weather_tool = Mock()
        weather_tool.name = "get_weather"
        weather_tool.description = "Get weather"

        math_tools = [add_tool, multiply_tool]
        weather_tools = [weather_tool]

        # Mock 클라이언트 설정
        servers = {
            "math": {"command": "python", "args": ["math.py"]},
            "weather": {"command": "python", "args": ["weather.py"]},
        }

        client = MultiServerMCPClient(servers)

        # Mock 클라이언트 주입
        mock_math_client = AsyncMock()
        mock_weather_client = AsyncMock()

        client._clients = {"math": mock_math_client, "weather": mock_weather_client}

        # load_mcp_tools를 mock
        with patch("pyhub.llm.agents.mcp.multi_client.load_mcp_tools") as mock_load:

            async def mock_load_side_effect(client, filter_tools=None):
                if client == mock_math_client:
                    return math_tools
                elif client == mock_weather_client:
                    return weather_tools
                return []

            mock_load.side_effect = mock_load_side_effect

            # 도구 가져오기
            tools = await client.get_tools()

            assert len(tools) == 3
            assert tools[0].name == "add"
            assert tools[1].name == "multiply"
            assert tools[2].name == "get_weather"

    @pytest.mark.asyncio
    async def test_get_tools_with_prefix(self):
        """prefix가 있을 때 도구 이름 변경 테스트"""
        # Mock 도구
        math_tool = Mock()
        math_tool.name = "add"
        math_tool.description = "Add numbers"

        servers = {"math": {"command": "python", "args": ["math.py"]}}
        client = MultiServerMCPClient(servers, prefix_tools=True)

        # Mock 클라이언트 주입
        mock_client = AsyncMock()
        client._clients = {"math": mock_client}

        with patch("pyhub.llm.agents.mcp.multi_client.load_mcp_tools") as mock_load:
            mock_load.return_value = [math_tool]

            tools = await client.get_tools()

            assert len(tools) == 1
            assert tools[0].name == "math.add"
            assert "[math]" in tools[0].description

    @pytest.mark.asyncio
    async def test_create_from_config(self):
        """설정에서 클라이언트 생성 테스트"""
        config = {
            "mcp": {
                "servers": {
                    "math": {"command": "python", "args": ["math.py"]},
                    "weather": {"command": "node", "args": ["weather.js"]},
                },
                "prefix_tools": True,
            }
        }

        client = await create_multi_server_client_from_config(config)

        assert isinstance(client, MultiServerMCPClient)
        assert len(client.servers) == 2
        assert "math" in client.servers
        assert "weather" in client.servers
        assert client.prefix_tools == True

    @pytest.mark.asyncio
    async def test_list_servers(self):
        """서버 목록 및 상태 확인 테스트"""
        servers = {
            "math": {"command": "python", "args": ["math.py"]},
            "weather": {"command": "python", "args": ["weather.py"]},
        }

        client = MultiServerMCPClient(servers)

        # 일부만 연결된 상황 시뮬레이션
        mock_client = AsyncMock()
        mock_client.list_tools.return_value = [{"name": "add"}, {"name": "multiply"}]
        client._clients = {"math": mock_client}

        status = await client.list_servers()

        assert len(status) == 2
        assert status["math"]["connected"] == True
        assert status["math"]["tools_count"] == 2
        assert status["weather"]["connected"] == False
        assert status["weather"]["tools_count"] == 0
