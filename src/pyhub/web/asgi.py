"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Mount
from pyhub.mcp import mcp

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

django_asgi_app = get_asgi_application()

application = Starlette(
    routes=[
        Mount("/mcp", app=mcp.sse_app()),  # `/mcp` 하위 경로 -> MCP SSE 서버
        Mount("/", app=django_asgi_app),  # 그 외 모든 경로 -> Django 앱
    ]
)