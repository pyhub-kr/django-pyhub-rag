"""MCP tools loader for pyhub agents."""

import logging
from typing import Any, Dict, List, Optional, Union

from ..base import Tool
from .client import MCPClient
from .wrapper import MCPTool

logger = logging.getLogger(__name__)


async def load_mcp_tools(
    client_or_params: Union[MCPClient, Any], filter_tools: Optional[List[str]] = None
) -> List[Tool]:
    """
    MCP 서버에서 도구를 로드하여 pyhub Tool로 변환

    Args:
        client_or_params: MCPClient 인스턴스 또는 서버 파라미터
        filter_tools: 로드할 도구 이름 필터 (None이면 모든 도구 로드)

    Returns:
        Tool 객체 리스트
    """

    # MCPClient가 아닌 경우 클라이언트 생성
    if isinstance(client_or_params, MCPClient):
        client = client_or_params
        # 이미 연결된 클라이언트 사용
        mcp_tools_def = await client.list_tools()
    else:
        # 서버 파라미터로 새 클라이언트 생성
        client = MCPClient(client_or_params)
        async with client.connect():
            mcp_tools_def = await client.list_tools()

    tools = []

    for tool_def in mcp_tools_def:
        tool_name = tool_def["name"]

        # 필터가 있는 경우 확인
        if filter_tools and tool_name not in filter_tools:
            logger.debug(f"Skipping tool '{tool_name}' (not in filter)")
            continue

        # MCPTool 래퍼 생성
        mcp_tool = MCPTool(tool_def, client)

        # pyhub Tool로 변환
        tool = Tool(
            name=mcp_tool.name,
            description=mcp_tool.description,
            func=mcp_tool.arun,  # 비동기 함수 사용
            args_schema=mcp_tool.args_schema,
            validation_level=mcp_tool.validation_level,
            pre_validators=[],
        )

        tools.append(tool)
        logger.info(f"Loaded MCP tool: {tool_name}")

    logger.info(f"Loaded {len(tools)} MCP tools")
    return tools


async def load_mcp_tools_from_config(config: Dict[str, Any]) -> List[Tool]:
    """
    설정 파일에서 MCP 서버 정보를 읽어 도구 로드

    Args:
        config: MCP 서버 설정
            {
                "command": "python",
                "args": ["/path/to/server.py"],
                "env": {"KEY": "value"},  # 선택적
                "filter_tools": ["tool1", "tool2"]  # 선택적
            }

    Returns:
        Tool 객체 리스트
    """
    try:
        from mcp import StdioServerParameters
    except ImportError:
        raise ImportError("MCP support requires 'mcp' package. " "Install it with: pip install mcp")

    # 서버 파라미터 생성
    server_params = StdioServerParameters(command=config["command"], args=config.get("args", []), env=config.get("env"))

    # 도구 필터
    filter_tools = config.get("filter_tools")

    # 도구 로드
    return await load_mcp_tools(server_params, filter_tools)
