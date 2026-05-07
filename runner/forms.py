from __future__ import annotations

from django import forms

from .models import RunJob

SCRIPT_EXTENSIONS = {
    "atlas": ".atl",
    "neptune": ".nep",
    "hydra": ".hyd",
    "chronos": ".chr",
    "athena": ".ath",
}
EXTRA_EXTENSIONS = {".csv", ".json", ".txt", ".pkl"}
MAX_SCRIPT_SIZE = 5 * 1024 * 1024
MAX_EXTRA_FILE_SIZE = 10 * 1024 * 1024
MAX_EXTRA_TOTAL_SIZE = 20 * 1024 * 1024
MAX_EXTRA_FILES = 20


class MultiClearableFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    """A FileField that accepts multiple files (list of UploadedFile)."""

    def clean(self, data, initial=None):
        if data in (None, "", [], ()):
            return [] if not self.required else super().clean(None, initial)
        if not isinstance(data, (list, tuple)):
            data = [data]
        cleaned = []
        for item in data:
            cleaned.append(super().clean(item, initial))
        return cleaned


class UploadRunForm(forms.ModelForm):
    extra_files = MultiFileField(
        required=False,
        widget=MultiClearableFileInput(attrs={"multiple": True}),
        help_text="Optional: upload CSV/data files referenced by load \"...\" next to the script.",
    )

    class Meta:
        model = RunJob
        fields = ["dsl", "uploaded_file"]

    @staticmethod
    def _suffix(name: str) -> str:
        from pathlib import Path

        return Path(name).suffix.lower()

    @staticmethod
    def _is_safe_name(name: str) -> bool:
        from pathlib import Path

        p = Path(name)
        return bool(p.name) and p.name == name and "/" not in name and "\\" not in name

    def clean_uploaded_file(self):
        f = self.cleaned_data["uploaded_file"]
        if f.size > MAX_SCRIPT_SIZE:
            raise forms.ValidationError("File too large (max 5MB).")
        if not self._is_safe_name(f.name):
            raise forms.ValidationError("Script filename must not contain path separators.")
        return f

    def clean_extra_files(self):
        files = self.cleaned_data.get("extra_files") or []
        if len(files) > MAX_EXTRA_FILES:
            raise forms.ValidationError(f"Too many extra files (max {MAX_EXTRA_FILES}).")
        total = 0
        for f in files:
            size = int(getattr(f, "size", 0))
            total += size
            if size > MAX_EXTRA_FILE_SIZE:
                raise forms.ValidationError(f"{f.name}: file too large (max 10MB).")
            if not self._is_safe_name(f.name):
                raise forms.ValidationError(f"{f.name}: filename must not contain path separators.")
            if self._suffix(f.name) not in EXTRA_EXTENSIONS:
                allowed = ", ".join(sorted(EXTRA_EXTENSIONS))
                raise forms.ValidationError(f"{f.name}: unsupported data file type. Allowed: {allowed}.")
        if total > MAX_EXTRA_TOTAL_SIZE:
            raise forms.ValidationError("Extra files too large (total max 20MB).")
        return files

    def clean(self):
        cleaned = super().clean()
        dsl = cleaned.get("dsl")
        uploaded = cleaned.get("uploaded_file")
        if dsl and uploaded:
            expected = SCRIPT_EXTENSIONS.get(dsl)
            if expected and self._suffix(uploaded.name) != expected:
                raise forms.ValidationError(f"{dsl} scripts must use the {expected} extension.")
        return cleaned

