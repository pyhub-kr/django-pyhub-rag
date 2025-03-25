import re

from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import TemplateView
from django.views.static import serve

from map.api import router as map_router
from ninja import NinjaAPI

#
# api
#

api = NinjaAPI()

if settings.SERVICE_DOMAIN:
    api.servers = [
        {"url": settings.SERVICE_DOMAIN},
    ]


if settings.ENABLE_MAP_SERVICE:
    api.add_router("/map", map_router)


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


#
# static serve
#


def static_pattern(prefix, document_root):
    return re_path(
        r"^%s(?P<path>.*)$" % re.escape(prefix.lstrip("/")),
        serve,
        kwargs={
            "document_root": document_root,
        },
    )


urlpatterns += [
    static_pattern(settings.STATIC_URL, settings.STATIC_ROOT),
    static_pattern(settings.MEDIA_URL, settings.MEDIA_ROOT),
]