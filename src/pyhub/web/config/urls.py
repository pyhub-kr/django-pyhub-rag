from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from map.api import router as map_router
from ninja import NinjaAPI

#
# api
#

api = NinjaAPI()
api.add_router("/map", map_router)

if settings.SERVICE_DOMAIN:
    api.servers = [
        {"url": settings.SERVICE_DOMAIN},
    ]


#
# views
#

urlpatterns = [
    path("", TemplateView.as_view(template_name="root.html"), name="root"),
    path("api/", api.urls),
]

if apps.is_installed("admin"):
    urlpatterns += [
        path("admin/", admin.site.urls),
    ]
