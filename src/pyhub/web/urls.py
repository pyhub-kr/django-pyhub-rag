import re

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
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
    path("", TemplateView.as_view(template_name="pyhub/root.html"), name="root"),
    path("ui/", include("pyhub.ui.urls")),
    path("doku/", include("pyhub.doku.urls")),
    path("mymcp/", include("pyhub.mcp.urls")),
    path("api/", api.urls),
]

if apps.is_installed("debug_toolbar"):
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))

if apps.is_installed("django_components"):
    urlpatterns.append(path("django-components/", include("django_components.urls")))

if apps.is_installed("django.contrib.admin"):
    urlpatterns.append(path("admin/", admin.site.urls))


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