from django.urls import include, path, re_path

from .views import frontend

urlpatterns = [
    path("api/ai-file-inspector/", include("ai_file_inspector.django_app.urls")),
    re_path(r"^(?P<path>.*)$", frontend),
]
