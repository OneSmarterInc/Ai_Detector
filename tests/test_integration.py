from types import SimpleNamespace
from unittest.mock import patch

from ai_file_inspector.django_app.views import owner
from ai_file_inspector.django_app.worker import submit_job
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse


@override_settings(ROOT_URLCONF="tests.integration_urls")
class HostIntegrationTests(TestCase):
    def test_namespaced_urls_support_a_parent_prefix(self):
        self.assertEqual(
            reverse("ai_file_inspector:info"), "/host/tools/inspector/info/"
        )
        response = self.client.get(reverse("ai_file_inspector:info"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("PDF", response.json()["limits_text"])
        self.assertEqual(self.client.get("/api/info/").status_code, 404)

    def test_upload_limits_do_not_change_parent_uploads(self):
        with patch("ai_file_inspector.django_app.uploads.MAX_FILE", 2):
            host = self.client.post(
                "/host/upload/", {"file": SimpleUploadedFile("host.txt", b"1234")}
            )
            self.assertEqual(host.json()["size"], 4)
            module = self.client.post(
                "/host/tools/inspector/jobs/",
                {"files": SimpleUploadedFile("module.txt", b"1234")},
            )
            self.assertEqual(module.status_code, 413)

    def test_host_mount_still_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post("/host/tools/inspector/jobs/", {"text": "test"})
        self.assertEqual(response.status_code, 403)


class HostServiceTests(SimpleTestCase):
    def test_authenticated_owner_survives_session_changes(self):
        first = SimpleNamespace(user=SimpleNamespace(pk=42, is_authenticated=True))
        second = SimpleNamespace(user=SimpleNamespace(pk=42, is_authenticated=True))
        other = SimpleNamespace(user=SimpleNamespace(pk=43, is_authenticated=True))
        self.assertEqual(owner(first), owner(second))
        self.assertNotEqual(owner(first), owner(other))
        self.assertLessEqual(len(owner(first)), 64)

    def test_existing_queue_can_receive_jobs(self):
        submitted = []
        with override_settings(AI_FILE_INSPECTOR={"SUBMIT_JOB": submitted.append}):
            submit_job("job-id")
        self.assertEqual(submitted, ["job-id"])
