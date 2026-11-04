import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.uploadhandler import StopUpload
from django.test import Client, SimpleTestCase, TestCase, override_settings

from ..core.percentages import percentage_breakdown
from .models import ScanJob
from .uploads import MAX_FILE, LimitedUploadHandler
from .worker import recover_interrupted_jobs, run_job


class PercentageTests(SimpleTestCase):
    def test_weighted_percentage_is_not_model_probability(self):
        d = dict(
            status="estimated",
            coverage="sampled",
            passages=[
                dict(tokens=100, ai_pattern_score=99),
                dict(tokens=300, ai_pattern_score=2),
                dict(tokens=100, ai_pattern_score=50),
            ],
        )
        r = percentage_breakdown(d)
        self.assertEqual((r["ai_like"], r["human_like"], r["uncertain"]), (20, 60, 20))
        self.assertTrue(r["sampled"])

    def test_no_score_is_not_zero_percent(self):
        for d in (
            None,
            {},
            dict(status="not_checked"),
            dict(status="estimated", passages=[]),
        ):
            self.assertIsNone(percentage_breakdown(d))

    def test_rounded_display_does_not_change_band(self):
        r = percentage_breakdown(
            dict(
                status="estimated",
                passages=[
                    dict(tokens=100, ai_pattern_score=80, signal_band="uncertain")
                ],
            )
        )
        self.assertEqual(r["uncertain"], 100)

    def test_percentages_sum_to_100(self):
        r = percentage_breakdown(
            dict(
                status="estimated",
                passages=[dict(tokens=1, ai_pattern_score=s) for s in [0, 50, 100]],
            )
        )
        self.assertEqual(r["human_like"] + r["ai_like"] + r["uncertain"], 100)

    def test_streaming_upload_limit(self):
        class Request:
            pass

        request = Request()
        handler = LimitedUploadHandler(request)
        handler.current = MAX_FILE
        with self.assertRaises(StopUpload):
            handler.receive_data_chunk(b"x", 0)
        self.assertIn("100 MB", request.upload_error)


class PortalTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.setting = override_settings(AI_FILE_INSPECTOR={"DATA_DIR": self.tmp.name})
        self.setting.enable()
        self.submit = patch("ai_file_inspector.django_app.views.submit_job")
        self.queue = self.submit.start()

    def tearDown(self):
        self.submit.stop()
        self.setting.disable()
        self.tmp.cleanup()

    def upload(self, name="test.txt", data=b"Hello"):
        return self.client.post(
            "/api/ai-file-inspector/jobs/", {"files": SimpleUploadedFile(name, data)}
        )

    def test_upload_queues_job_and_hides_storage_paths(self):
        response = self.upload()
        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["files"][0]["name"], "test.txt")
        self.assertNotIn("stored", body["files"][0])
        self.queue.assert_called_once()

    def test_paste_and_empty_validation(self):
        self.assertEqual(
            self.client.post("/api/ai-file-inspector/jobs/", {}).status_code, 400
        )
        self.assertEqual(
            self.client.post("/api/ai-file-inspector/jobs/", {"text": " "}).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                "/api/ai-file-inspector/jobs/", {"text": "Example text"}
            ).status_code,
            202,
        )

    def test_unsupported_and_too_many_files(self):
        self.assertEqual(self.upload("bad.exe").status_code, 400)
        self.assertEqual(
            self.client.post(
                "/api/ai-file-inspector/jobs/",
                {"files": [SimpleUploadedFile(f"{i}.txt", b"x") for i in range(11)]},
            ).status_code,
            400,
        )

    def test_paste_character_limit(self):
        self.assertEqual(
            self.client.post(
                "/api/ai-file-inspector/jobs/", {"text": "x" * 200001}
            ).status_code,
            400,
        )

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post("/api/ai-file-inspector/jobs/", {"text": "hello"}).status_code,
            403,
        )
        info = client.get("/api/ai-file-inspector/info/").json()
        self.assertEqual(
            client.post(
                "/api/ai-file-inspector/jobs/",
                {"text": "hello"},
                HTTP_X_CSRFTOKEN=info["csrf_token"],
            ).status_code,
            202,
        )

    def test_sessions_isolate_reports_and_assets(self):
        job = self.upload().json()["id"]
        other = Client()
        for suffix in ["", "report/", "assets/not-allowed.png"]:
            self.assertEqual(
                other.get(f"/api/ai-file-inspector/jobs/{job}/{suffix}").status_code,
                404,
            )
        self.assertEqual(other.get("/api/ai-file-inspector/jobs/").json()["jobs"], [])

    def test_nonlisted_asset_is_not_served(self):
        job = self.upload().json()["id"]
        self.assertEqual(
            self.client.get(
                f"/api/ai-file-inspector/jobs/{job}/assets/secret.key"
            ).status_code,
            404,
        )

    def test_running_job_cannot_be_deleted(self):
        job = self.upload().json()["id"]
        self.assertEqual(
            self.client.delete(f"/api/ai-file-inspector/jobs/{job}/").status_code, 409
        )

    def test_completed_job_delete_removes_uploads(self):
        job = self.upload().json()["id"]
        ScanJob.objects.filter(id=job).update(status="complete")
        self.assertEqual(
            self.client.delete(f"/api/ai-file-inspector/jobs/{job}/").status_code, 200
        )
        self.assertFalse((Path(self.tmp.name) / "jobs" / job).exists())

    def test_short_text_worker_and_download(self):
        job = self.upload().json()["id"]
        run_job(job)
        result = self.client.get(f"/api/ai-file-inspector/jobs/{job}/").json()
        self.assertEqual(result["status"], "complete")
        self.assertIsNone(result["results"][0]["breakdown"])
        self.assertEqual(result["results"][0]["file"], "test.txt")
        self.assertEqual(
            self.client.get(f"/api/ai-file-inspector/jobs/{job}/report/").status_code,
            200,
        )

    def test_corrupt_file_has_clear_error_and_finishes(self):
        job = self.upload("bad.pdf", b"bad pdf").json()["id"]
        run_job(job)
        result = self.client.get(f"/api/ai-file-inspector/jobs/{job}/").json()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["results"][0]["status"], "failed")
        self.assertNotIn(self.tmp.name, result["results"][0]["error"])

    def test_restart_marks_unfinished_job(self):
        job = self.upload().json()["id"]
        recover_interrupted_jobs()
        self.assertEqual(
            self.client.get(f"/api/ai-file-inspector/jobs/{job}/").json()["status"],
            "failed",
        )

    def test_paste_and_file_are_not_combined_silently(self):
        response = self.client.post(
            "/api/ai-file-inspector/jobs/",
            {"text": "hello", "files": SimpleUploadedFile("a.txt", b"test")},
        )
        self.assertEqual(response.status_code, 400)
