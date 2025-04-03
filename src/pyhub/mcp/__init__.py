from typing import cast

from django.conf import settings
from django.utils.functional import SimpleLazyObject
from mcp.server.fastmcp import FastMCP


# https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#server


def _setup_mcp() -> FastMCP:
    """Initializes the FastMCP instance."""

    kwargs = settings.FASTMCP_SETTINGS.model_dump()
    return FastMCP(**kwargs)


# 타입을 명시해야만, IDE에 의한 자동완성이 지원됩니다.
mcp = cast(FastMCP, SimpleLazyObject(_setup_mcp))
