from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.urls import reverse

from pyhub.llm.json import json_dumps


async def index(request):
    pass


# TODO: @require_POST
async def sse(request):
    """
    Content-Type: text/event-stream: 응답 본문이 SSE 형식임을 명시하는 가장 중요한 헤더입니다.
    Cache-Control: no-cache: 프록시나 브라우저가 응답을 캐싱하지 않도록 합니다.
    Connection: keep-alive: 클라이언트와의 연결을 계속 유지하여 데이터를 지속적으로 푸시할 수 있도록 합니다.
    X-Accel-Buffering: no (Nginx 사용 시): Nginx가 응답을 버퍼링하지 않도록 설정하여 실시간 스트리밍을 보장합니다.
    """

    # mcp/server/sse.py 의 connect_sse에서는 uuid4().hex를 통해 session_id를 발급

    async def make_res():
        yield "data: hello"
        yield "data: world"

    response = StreamingHttpResponse(
        make_res(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


async def messages(request):
    return HttpResponse("messages response")


async def config_detail(request) -> HttpResponse:
    url = request.build_absolute_uri(reverse("mcp:sse"))
    mcp_config = json_dumps(
        {
            "mcpServers": {
                "django-pyhub-rag": {
                    "command": "uv",
                    "args": [],
                    "url": url,
                    "transport": "sse",
                },
            }
        },
        indent=2,
    )
    return render(
        request,
        "mcp/config_detail.html",
        {
            "mcp_config": mcp_config,
        },
    )
