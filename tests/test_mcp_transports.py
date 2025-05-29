"""Tests for MCP transport implementations."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from pyhub.llm.agents.mcp.transports import (
    StdioTransport,
    StreamableHTTPTransport,
    create_transport,
    infer_transport_type
)
from pyhub.llm.agents.mcp import MCPClient


class TestTransportInference:
    """Transport 타입 추론 테스트"""
    
    def test_infer_stdio_from_command(self):
        """command 필드로 stdio 추론"""
        config = {"command": "python", "args": ["server.py"]}
        assert infer_transport_type(config) == "stdio"
    
    def test_infer_http_from_url(self):
        """url 필드로 streamable_http 추론"""
        config = {"url": "http://localhost:3000/mcp"}
        assert infer_transport_type(config) == "streamable_http"
    
    def test_explicit_transport_type(self):
        """명시적 transport 지정"""
        config = {
            "transport": "streamable_http",
            "url": "http://localhost:3000",
            "command": "ignored"  # transport가 명시되면 무시됨
        }
        assert infer_transport_type(config) == "streamable_http"
    
    def test_infer_error_no_hints(self):
        """추론 불가능한 경우 에러"""
        config = {"some_field": "value"}
        with pytest.raises(ValueError, match="Cannot infer transport type"):
            infer_transport_type(config)


class TestTransportCreation:
    """Transport 생성 테스트"""
    
    def test_create_stdio_transport(self):
        """stdio transport 생성"""
        config = {
            "transport": "stdio",
            "command": "python",
            "args": ["server.py"],
            "env": {"KEY": "value"}
        }
        
        with patch('mcp.StdioServerParameters') as mock_params:
            transport = create_transport(config)
            
            assert isinstance(transport, StdioTransport)
            mock_params.assert_called_once_with(
                command="python",
                args=["server.py"],
                env={"KEY": "value"}
            )
    
    def test_create_http_transport(self):
        """HTTP transport 생성"""
        config = {
            "transport": "streamable_http",
            "url": "http://localhost:3000/mcp",
            "headers": {"Authorization": "Bearer token"}
        }
        
        transport = create_transport(config)
        
        assert isinstance(transport, StreamableHTTPTransport)
        assert transport.url == "http://localhost:3000/mcp"
        assert transport.headers == {"Authorization": "Bearer token"}
    
    def test_create_transport_auto_infer(self):
        """transport 타입 자동 추론"""
        config = {"url": "http://localhost:3000/mcp"}
        
        transport = create_transport(config)
        
        assert isinstance(transport, StreamableHTTPTransport)
    
    def test_create_unsupported_transport(self):
        """지원하지 않는 transport 타입"""
        config = {"transport": "websocket"}
        
        with pytest.raises(ValueError, match="Unsupported transport type"):
            create_transport(config)


class TestStdioTransport:
    """StdioTransport 테스트"""
    
    @pytest.mark.asyncio
    async def test_stdio_connect(self):
        """stdio 연결 테스트"""
        mock_params = Mock()
        transport = StdioTransport(mock_params)
        
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        
        with patch('mcp.client.stdio.stdio_client') as mock_client:
            # async context manager 시뮬레이션
            mock_client.return_value.__aenter__.return_value = (mock_read, mock_write)
            mock_client.return_value.__aexit__.return_value = None
            
            async with transport.connect() as (read, write):
                assert read == mock_read
                assert write == mock_write
                mock_client.assert_called_once_with(mock_params)


class TestStreamableHTTPTransport:
    """StreamableHTTPTransport 테스트"""
    
    @pytest.mark.asyncio
    async def test_http_connect(self):
        """HTTP 연결 테스트"""
        url = "http://localhost:3000/mcp"
        headers = {"Authorization": "Bearer token"}
        transport = StreamableHTTPTransport(url, headers)
        
        # StreamableHTTPTransport는 초기화 시 url과 headers를 저장
        assert transport.url == url
        assert transport.headers == headers


class TestMCPClientWithTransport:
    """Transport를 사용하는 MCPClient 테스트"""
    
    @pytest.mark.asyncio
    async def test_client_with_config(self):
        """설정 기반 클라이언트 생성"""
        config = {
            "transport": "streamable_http",
            "url": "http://localhost:3000/mcp"
        }
        
        client = MCPClient(config)
        
        assert client.transport is not None
        assert isinstance(client.transport, StreamableHTTPTransport)
        assert client.server_params is None