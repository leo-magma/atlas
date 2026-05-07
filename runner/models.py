from __future__ import annotations

from django.db import models


class RunJob(models.Model):
    DSL_CHOICES = [
        ("atlas", "Atlas (.atl)"),
        ("neptune", "Neptune (.nep)"),
        ("hydra", "Hydra (.hyd)"),
        ("chronos", "Chronos (.chr)"),
        ("athena", "Athena (.ath)"),
    ]

    dsl = models.CharField(max_length=20, choices=DSL_CHOICES)
    uploaded_file = models.FileField(upload_to="uploads/%Y%m%d/")

    status = models.CharField(
        max_length=20,
        default="queued",
        choices=[
            ("queued", "queued"),
            ("running", "running"),
            ("succeeded", "succeeded"),
            ("failed", "failed"),
            ("cancelled", "cancelled"),
        ],
    )
    progress = models.PositiveSmallIntegerField(default=0)  # 0..100

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    output_text = models.TextField(blank=True, default="")
    error_text = models.TextField(blank=True, default="")
    cancel_requested = models.BooleanField(default=False)
    input_manifest = models.TextField(blank=True, default="[]")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

