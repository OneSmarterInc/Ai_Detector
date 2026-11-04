"""Static React delivery for the standalone launcher only."""

import mimetypes

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def frontend(request, path=""):
    if path.startswith("api/"):
        return JsonResponse({"error": "Endpoint not found."}, status=404)
    root = settings.FRONTEND_DIST.resolve()
    target = (root / (path or "index.html")).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise Http404("Build the React frontend first.")
    response = FileResponse(
        target.open("rb"),
        content_type=mimetypes.guess_type(str(target))[0] or "application/octet-stream",
    )
    response["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"
    )
    return response
