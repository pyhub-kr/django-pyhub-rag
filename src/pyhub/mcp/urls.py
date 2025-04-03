from django.urls import path
from . import views

app_name = "mcp"

urlpatterns = [
    path("", views.index, name="index"),
    path("sse/", views.sse, name="sse"),
    path("messages/", views.messages, name="messages"),
    path("config/", views.config_detail, name="config-detail"),
]
