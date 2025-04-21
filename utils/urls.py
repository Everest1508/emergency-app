from django.urls import path
from .views import log_viewer

urlpatterns = [
    path("logs/", log_viewer, name="log_viewer"),
]
