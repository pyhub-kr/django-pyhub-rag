from django.conf import settings
from ninja import NinjaAPI

from .map import router as map_router

api = NinjaAPI()

api.add_router("/map", map_router)


if settings.SERVICE_DOMAIN:
    api.servers = [
        {"url": settings.SERVICE_DOMAIN},
    ]
