"""MCP transport implementations."""

import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class Transport(ABC):
    """Base transport interface for MCP connections."""

    @abstractmethod
    @asynccontextmanager
    async def connect(self):
        """Establish connection and return read/write streams."""
        pass


class StdioTransport(Transport):
    """Standard I/O transport for MCP servers."""

    def __init__(self, server_params: Any):
        """
        Args:
            server_params: StdioServerParameters instance
        """
        self.server_params = server_params

    @asynccontextmanager
    async def connect(self):
        """Connect to MCP server via stdio."""
        try:
            from mcp.client.stdio import stdio_client
        except ImportError:
            raise ImportError("MCP stdio support requires 'mcp' package. " "Install it with: pip install mcp")

        async with stdio_client(self.server_params) as (read, write):
            logger.debug(f"Connected to stdio server: {self.server_params.command}")
            yield read, write


class StreamableHTTPTransport(Transport):
    """Streamable HTTP transport for MCP servers."""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        """
        Args:
            url: HTTP endpoint URL
            headers: Optional HTTP headers
        """
        self.url = url
        self.headers = headers or {}

    @asynccontextmanager
    async def connect(self):
        """Connect to MCP server via streamable HTTP."""
        try:
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError:
            raise ImportError("MCP streamable HTTP support requires 'mcp' package. " "Install it with: pip install mcp")

        # streamablehttp_client returns (read, write, _)
        async with streamablehttp_client(self.url, self.headers) as (read, write, _):
            logger.debug(f"Connected to HTTP server: {self.url}")
            yield read, write


def create_transport(config: Dict[str, Any]) -> Transport:
    """
    Create appropriate transport based on configuration.

    Args:
        config: Server configuration dict

    Returns:
        Transport instance
    """
    # transport 타입 추론
    transport_type = config.get("transport")
    if not transport_type:
        transport_type = infer_transport_type(config)

    if transport_type == "stdio":
        # stdio transport 사용
        try:
            from mcp import StdioServerParameters
        except ImportError:
            raise ImportError("MCP support requires 'mcp' package. " "Install it with: pip install mcp")

        if "command" not in config:
            raise ValueError("stdio transport requires 'command' field")

        server_params = StdioServerParameters(
            command=config["command"], args=config.get("args", []), env=config.get("env")
        )

        return StdioTransport(server_params)

    elif transport_type == "streamable_http":
        # streamable HTTP transport 사용
        if "url" not in config:
            raise ValueError("streamable_http transport requires 'url' field")

        return StreamableHTTPTransport(url=config["url"], headers=config.get("headers", {}))

    else:
        raise ValueError(f"Unsupported transport type: {transport_type}")


def infer_transport_type(config: Dict[str, Any]) -> str:
    """
    Infer transport type from configuration.

    Args:
        config: Server configuration dict

    Returns:
        Transport type string
    """
    # 명시적으로 지정된 경우
    if "transport" in config:
        return config["transport"]

    # URL이 있으면 HTTP
    if "url" in config:
        return "streamable_http"

    # command가 있으면 stdio
    if "command" in config:
        return "stdio"

    raise ValueError(
        "Cannot infer transport type. " "Provide either 'transport', 'url' (for HTTP), or 'command' (for stdio)"
    )
