import logging
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections
from django.utils import timezone
from django.utils.module_loading import import_string

from ..core.percentages import percentage_breakdown
from .conf import data_root, option
from .models import ScanJob

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ai-file-inspector")
logger = logging.getLogger(__name__)


def update(job_id, **values):
    ScanJob.objects.filter(id=job_id).update(updated=timezone.now(), **values)


def run_job(job_id):
    close_old_connections()
    try:
        from ..core import scanner as inspector

        job = ScanJob.objects.get(id=job_id)
        folder = data_root() / "jobs" / str(job.id)
        assets = folder / "assets"
        assets.mkdir(exist_ok=True)
        results = []
        counter = [0]
        for i, item in enumerate(job.files, 1):
            update(
                job_id,
                status="running",
                progress=f"Checking {i} of {len(job.files)}: {item['name']}",
            )
            try:
                result = inspector.inspect_file(
                    folder / "uploads" / item["stored"], assets, counter
                )
                result["file"] = item["name"]
                for picture in result.get("images", []):
                    if picture.get("source") == item["stored"]:
                        picture["source"] = item["name"]
                result["breakdown"] = percentage_breakdown(
                    result.get("text", {}).get("ai_detection")
                )
            except Exception:
                logger.exception(
                    "File check failed for job %s, file %s", job_id, item["stored"]
                )
                result = {
                    "file": item["name"],
                    "status": "failed",
                    "error": "This file could not be read. Open it in its usual app, save a fresh unlocked copy, and try again.",
                }
            results.append(result)
            update(job_id, results=results)
        update(
            job_id, status="complete", progress="Your report is ready.", results=results
        )
    except Exception:
        logger.exception("Job %s failed", job_id)
        update(
            job_id,
            status="failed",
            progress="Scan stopped",
            error="This scan could not finish. Try again or restart the portal.",
        )
    finally:
        close_old_connections()


def submit_job(job_id):
    """An existing application can dispatch run_job through its own task queue."""
    submit = option("SUBMIT_JOB")
    if submit:
        callback = import_string(submit) if isinstance(submit, str) else submit
        callback(str(job_id))
    else:
        _executor.submit(run_job, job_id)


def recover_interrupted_jobs():
    ScanJob.objects.filter(status__in=["queued", "running"]).update(
        status="failed",
        error="The portal restarted before this scan finished. Please upload these files again.",
        progress="Scan interrupted",
    )
