"""Multi-server MCP client implementation."""

import asyncio
import logging
from typing import Any, Dict, List

from ..base import Tool
from .client import MCPClient
from .loader import load_mcp_tools

logger = logging.getLogger(__name__)


class MultiServerMCPClient:
    """여러 MCP 서버를 동시에 관리하는 클라이언트"""

    def __init__(self, servers: Dict[str, Dict[str, Any]], prefix_tools: bool = False):
        """
        Args:
            servers: 서버 설정 딕셔너리
                {
                    "server_name": {
                        "command": "python",
                        "args": ["/path/to/server.py"],
                        "transport": "stdio",  # 현재는 stdio만 지원
                        "filter_tools": ["tool1", "tool2"],  # 선택적
                    }
                }
            prefix_tools: 도구 이름에 서버 이름을 prefix로 추가할지 여부
        """
        self.servers = servers
        self.prefix_tools = prefix_tools
        self._clients: Dict[str, MCPClient] = {}
        self._active_connections: Dict[str, Any] = {}

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        # 모든 서버에 동시 연결
        tasks = []
        for server_name, config in self.servers.items():
            task = asyncio.create_task(self._connect_server(server_name, config))
            tasks.append(task)

        # 모든 연결 대기
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 연결 실패 로그
        for server_name, result in zip(self.servers.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Failed to connect to '{server_name}': {result}")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        # 모든 연결 종료
        for server_name in list(self._active_connections.keys()):
            try:
                await self._active_connections[server_name].__aexit__(None, None, None)
                del self._active_connections[server_name]
                logger.info(f"Disconnected from '{server_name}'")
            except Exception as e:
                logger.error(f"Error disconnecting from '{server_name}': {e}")

    async def _connect_server(self, server_name: str, config: Dict[str, Any]):
        """개별 서버에 연결"""
        try:
            # Transport 타입 자동 추론
            from .transports import infer_transport_type

            # transport 타입이 명시되지 않은 경우 추론
            if "transport" not in config:
                config["transport"] = infer_transport_type(config)

            # 클라이언트 생성 (새로운 설정 기반 방식)
            client = MCPClient(config)

            # 연결 컨텍스트 매니저 저장
            connection_context = client.connect()
            # 연결 시작
            await connection_context.__aenter__()

            self._clients[server_name] = client
            self._active_connections[server_name] = connection_context

            logger.info(f"Connected to '{server_name}' successfully via {config['transport']}")

        except Exception as e:
            logger.error(f"Failed to connect to '{server_name}': {e}")
            raise

    async def get_tools(self) -> List[Tool]:
        """모든 서버에서 도구를 가져와 통합"""
        all_tools = []

        # 각 서버에서 도구 가져오기
        for server_name, client in self._clients.items():
            try:
                # 서버 설정에서 필터 가져오기
                filter_tools = self.servers[server_name].get("filter_tools")

                # 도구 로드
                tools = await load_mcp_tools(client, filter_tools)

                # 도구 이름에 prefix 추가 (옵션)
                if self.prefix_tools:
                    for tool in tools:
                        original_name = tool.name
                        tool.name = f"{server_name}.{original_name}"
                        tool.description = f"[{server_name}] {tool.description}"
                        logger.debug(f"Renamed tool '{original_name}' to '{tool.name}'")

                all_tools.extend(tools)
                logger.info(f"Loaded {len(tools)} tools from '{server_name}'")

            except Exception as e:
                logger.error(f"Failed to load tools from '{server_name}': {e}")
                # 실패한 서버는 건너뛰고 계속 진행
                continue

        logger.info(f"Total {len(all_tools)} tools loaded from {len(self._clients)} servers")
        return all_tools

    async def list_servers(self) -> Dict[str, Dict[str, Any]]:
        """연결된 서버 목록과 상태 반환"""
        server_status = {}

        for server_name, config in self.servers.items():
            status = {"config": config, "connected": server_name in self._clients, "tools_count": 0}

            # 연결된 경우 도구 수 확인
            if server_name in self._clients:
                try:
                    tools = await self._clients[server_name].list_tools()
                    status["tools_count"] = len(tools)
                except Exception as e:
                    status["error"] = str(e)

            server_status[server_name] = status

        return server_status


async def create_multi_server_client_from_config(config: Dict[str, Any]) -> MultiServerMCPClient:
    """설정에서 MultiServerMCPClient 생성"""
    servers = {}

    # mcp.servers 섹션에서 서버 설정 읽기
    mcp_config = config.get("mcp", {})
    servers_config = mcp_config.get("servers", {})

    for server_name, server_config in servers_config.items():
        # 필수 필드 확인
        if "command" not in server_config:
            logger.warning(f"Server '{server_name}' missing 'command', skipping")
            continue

        servers[server_name] = server_config

    if not servers:
        raise ValueError("No valid MCP servers found in configuration")

    # prefix_tools 옵션
    prefix_tools = mcp_config.get("prefix_tools", False)

    return MultiServerMCPClient(servers, prefix_tools=prefix_tools)
