from django.apps import apps
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("api.urls")),
]

if apps.is_installed("admin"):
    urlpatterns += [
        path("admin/", admin.site.urls),
    ]
