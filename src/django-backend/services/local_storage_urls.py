"""URL patterns for local filesystem storage in development.

Only included when STORAGE_BACKEND=local.
"""

from pathlib import Path

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve


@csrf_exempt
def local_media_upload(request: HttpRequest, path_key: str) -> HttpResponse:
    """Accept PUT uploads for local development storage."""
    if request.method != "PUT":
        return HttpResponse(status=405)

    storage_dir = Path(settings.BASE_DIR) / "media" / "storage"
    file_path = storage_dir / path_key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(request.body)
    return HttpResponse(status=200)


urlpatterns = [
    path(
        "media/storage/<path:path>",
        serve,
        {"document_root": settings.BASE_DIR / "media" / "storage"},
    ),
    path(
        "media/upload/<path:path_key>",
        local_media_upload,
    ),
]
