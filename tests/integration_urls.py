"""A sample parent URL configuration: no standalone settings or static routes."""

from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def host_upload(request):
    return JsonResponse({"size": request.FILES["file"].size})


urlpatterns = [
    path("host/tools/inspector/", include("ai_file_inspector.django_app.urls")),
    path("host/upload/", host_upload),
]
