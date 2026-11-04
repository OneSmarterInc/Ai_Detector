import hashlib
import shutil
from importlib.resources import files
from pathlib import Path

from django.http import FileResponse, Http404, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_GET, require_http_methods

from .conf import data_root, option
from .models import ScanJob
from .uploads import MAX_BATCH, MAX_FILE, LimitedUploadHandler
from .worker import submit_job


def owner(request):
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return "user:" + hashlib.sha256(str(user.pk).encode()).hexdigest()[:59]
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def payload(job, details=True):
    data = dict(
        id=str(job.id),
        status=job.status,
        progress=job.progress,
        created=job.created.isoformat(),
        files=[{"name": x["name"], "size": x["size"]} for x in job.files],
        error=job.error,
    )
    if details:
        data["results"] = job.results
    return data


@require_GET
def info(request):
    from ..core import detector as ai_detector
    from ..core import scanner as inspector

    return JsonResponse(
        dict(
            csrf_token=get_token(request),
            model=ai_detector.MODEL_NAME,
            model_ready=ai_detector.installed(),
            extensions=sorted(inspector.SUPPORTED),
            max_file_bytes=MAX_FILE,
            max_batch_bytes=MAX_BATCH,
            max_files=10,
            minimum_words=100,
            max_characters=200000,
            max_sections=12,
            pdf_pages=300,
            image_pixels=40000000,
            limits_text=files("ai_file_inspector.resources")
            .joinpath("file-limits.txt")
            .read_text(encoding="utf-8"),
        )
    )


@csrf_exempt
def jobs(request):
    # Install only for this endpoint, before CSRF middleware parses the body.
    # The inner view still enforces Django's normal CSRF checks.
    if request.method == "POST":
        request.upload_handlers.insert(0, LimitedUploadHandler(request))
    return _jobs(request)


@csrf_protect
@require_http_methods(["GET", "POST"])
def _jobs(request):
    key = owner(request)
    if request.method == "GET":
        return JsonResponse(
            {
                "jobs": [
                    payload(j, False)
                    for j in ScanJob.objects.filter(owner=key).order_by("-created")[:20]
                ]
            }
        )
    from ..core import scanner as inspector

    files = request.FILES.getlist("files")
    if getattr(request, "upload_error", None):
        return JsonResponse({"error": request.upload_error}, status=413)
    text = request.POST.get("text", "")
    if files and text:
        return JsonResponse(
            {"error": "Choose files or paste text, not both in one scan."}, status=400
        )
    if not files and not text.strip():
        return JsonResponse(
            {"error": "Choose a file or paste some English writing."}, status=400
        )
    if len(files) > 10:
        return JsonResponse({"error": "Choose up to 10 files per batch."}, status=400)
    if len(text) > 200000:
        return JsonResponse({"error": "Paste up to 200,000 characters."}, status=400)
    if any(x.size > MAX_FILE for x in files) or sum(x.size for x in files) > MAX_BATCH:
        return JsonResponse(
            {"error": "Use files up to 100 MB each and 500 MB per batch."}, status=413
        )
    if any(Path(x.name).suffix.lower() not in inspector.SUPPORTED for x in files):
        return JsonResponse(
            {
                "error": "One of these file types is not supported. Open File limits for the full list."
            },
            status=400,
        )
    if ScanJob.objects.filter(status__in=["queued", "running"]).count() >= option(
        "MAX_QUEUED_JOBS", 5
    ):
        return JsonResponse(
            {
                "error": "There are several scans waiting. Wait for one to finish, then try again."
            },
            status=429,
        )
    job = ScanJob.objects.create(owner=key)
    folder = data_root() / "jobs" / str(job.id)
    uploads = folder / "uploads"
    items = []
    try:
        uploads.mkdir(parents=True)
        for i, file in enumerate(files, 1):
            stored = str(i) + Path(file.name).suffix.lower()
            with (uploads / stored).open("wb") as stream:
                for block in file.chunks():
                    stream.write(block)
            items.append(
                {
                    "name": Path(file.name.replace("\\", "/")).name[:240],
                    "stored": stored,
                    "size": file.size,
                }
            )
        if text:
            data = text.encode("utf-8")
            (uploads / "1.txt").write_bytes(data)
            items = [{"name": "Pasted text.txt", "stored": "1.txt", "size": len(data)}]
        job.files = items
        job.save(update_fields=["files"])
        submit_job(job.id)
    except Exception:
        if (
            folder.exists()
            and folder.resolve().parent == (data_root() / "jobs").resolve()
        ):
            shutil.rmtree(folder, ignore_errors=True)
        job.delete()
        return JsonResponse(
            {"error": "Could not save this scan. Check free disk space and try again."},
            status=500,
        )
    return JsonResponse(payload(job), status=202)


def owned_job(request, job_id):
    return get_object_or_404(ScanJob, id=job_id, owner=owner(request))


@require_http_methods(["GET", "DELETE"])
def job_detail(request, job_id):
    job = owned_job(request, job_id)
    if request.method == "GET":
        return JsonResponse(payload(job))
    if job.status in ["queued", "running"]:
        return JsonResponse(
            {"error": "Wait for this scan to finish before deleting it."}, status=409
        )
    folder = data_root() / "jobs" / str(job.id)
    if folder.exists() and folder.resolve().parent == (data_root() / "jobs").resolve():
        shutil.rmtree(folder)
    job.delete()
    return JsonResponse({"deleted": True})


@require_GET
def report_download(request, job_id):
    job = owned_job(request, job_id)
    response = JsonResponse(
        payload(job), json_dumps_params={"ensure_ascii": False, "indent": 2}
    )
    response["Content-Disposition"] = 'attachment; filename="inspection-report.json"'
    return response


@require_GET
def asset(request, job_id, name):
    job = owned_job(request, job_id)
    allowed = {
        Path(v["file"]).name
        for r in job.results
        for image in r.get("images", [])
        for v in image.get("visuals", [])
    }
    if name not in allowed:
        raise Http404
    path = data_root() / "jobs" / str(job.id) / "assets" / name
    if not path.is_file():
        raise Http404
    return FileResponse(path.open("rb"), content_type="image/png")
