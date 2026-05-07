import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "suiteui.settings")
django = pytest.importorskip("django")
django.setup()

from django.test import Client, TestCase, override_settings

from runner.models import RunJob


class RunnerSecurityTests(TestCase):
    def test_job_status_requires_session_access(self):
        job = RunJob.objects.create(dsl="atlas", uploaded_file="uploads/20240101/example.atl")
        with override_settings(SUITEUI_REQUIRE_JOB_SESSION=True):
            res = Client().get(f"/job/{job.id}/status/")
        assert res.status_code == 403

    def test_job_input_file_respects_manifest_and_session(self):
        tmp = Path(self._testMethodName)
        media_root = Path.cwd() / ".tmp_test_media" / tmp
        job_dir = media_root / "uploads" / "20240101"
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "script.atl").write_text("x = load \"prices.csv\"\n", encoding="utf-8")
        (job_dir / "secret.txt").write_text("secret\n", encoding="utf-8")
        with override_settings(MEDIA_ROOT=media_root, SUITEUI_REQUIRE_JOB_SESSION=True):
            job = RunJob.objects.create(
                dsl="atlas",
                uploaded_file="uploads/20240101/script.atl",
                input_manifest=json.dumps(["script.atl"]),
            )
            client = Client()
            session = client.session
            session["suiteui_job_ids"] = [job.id]
            session.save()
            assert client.get(f"/job/{job.id}/input/script.atl/").status_code == 200
            assert client.get(f"/job/{job.id}/input/secret.txt/").status_code == 404

    def test_cancel_requires_post(self):
        job = RunJob.objects.create(dsl="atlas", uploaded_file="uploads/20240101/script.atl")
        with override_settings(SUITEUI_REQUIRE_JOB_SESSION=False):
            assert Client().get(f"/job/{job.id}/cancel/").status_code == 405
