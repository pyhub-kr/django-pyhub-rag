import httpx
from django.conf import settings
from ninja import Query, Router

from .response import NaverMapRouterResponse

router = Router()


if settings.NCP_MAP_CLIENT_ID and settings.NCP_MAP_CLIENT_SECRET:

    @router.get(
        "/naver/route/",
        description="네이버 지도 길찾기 API",
        tags=["naver"],
        response=NaverMapRouterResponse,
    )
    async def naver_map_route(
        request,
        start: str = Query(
            ...,
            description="출발지 경도,위도",
            regex=r"^\d+\.\d+,\d+\.\d+$",
            # examples={"강남역": "127.027619,37.497952"},
        ),
        goal: str = Query(
            ...,
            description="목적지 경도,위도",
            regex=r"^\d+\.\d+,\d+\.\d+$",
            # examples={"홍대입구역": "126.92361,37.55667"},
        ),
        option: str = Query(
            "trafast",
            description="""경로 조회 옵션
            - trafast: 실시간 빠른 길
            - tracomfort: 실시간 편한 길
            - traoptimal: 실시간 최적
            - traavoidtoll: 무료 우선
            - traavoidcaronly: 자동차 전용 도로 회피 우선""",
            choices=["trafast", "tracomfort", "traoptimal", "traavoidtoll", "traavoidcaronly"],
        ),
    ):
        """
        네이버 지도 경로 검색 Direction 5 API를 호출하여 경로를 반환합니다.

        https://api.ncloud-docs.com/docs/ai-naver-mapsdirections-driving
        https://console.ncloud.com/naver-service/application
        """
        api_url = "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving"
        headers = {
            "X-NCP-APIGW-API-KEY-ID": settings.NCP_MAP_CLIENT_ID,
            "X-NCP-APIGW-API-KEY": settings.NCP_MAP_CLIENT_SECRET,
        }
        params = {
            "start": start,
            "goal": goal,
            "option": option,
        }

        async with httpx.AsyncClient() as client:
            res = await client.get(api_url, headers=headers, params=params)

            import json

            s = json.dumps(res.json(), indent=4, ensure_ascii=False)
            open("naver_map.json", "wt").write(s)

            return res.json()
