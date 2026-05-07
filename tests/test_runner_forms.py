import os

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "suiteui.settings")
django = pytest.importorskip("django")
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile

from runner.forms import UploadRunForm


def _file(name: str, body: bytes = b"x") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, body)


def test_upload_form_requires_matching_script_extension():
    form = UploadRunForm(
        data={"dsl": "atlas"},
        files={"uploaded_file": _file("bad.nep")},
    )
    assert not form.is_valid()
    assert "atlas scripts must use the .atl extension" in str(form.errors)


def test_upload_form_rejects_unsupported_extra_file_extension():
    form = UploadRunForm(
        data={"dsl": "atlas"},
        files={
            "uploaded_file": _file("ok.atl"),
            "extra_files": [_file("payload.exe")],
        },
    )
    assert not form.is_valid()
    assert "unsupported data file type" in str(form.errors)


def test_upload_form_accepts_script_and_csv_data():
    form = UploadRunForm(
        data={"dsl": "atlas"},
        files={
            "uploaded_file": _file("ok.atl"),
            "extra_files": [_file("prices.csv", b"date,close\n2024-01-01,100\n")],
        },
    )
    assert form.is_valid(), form.errors
