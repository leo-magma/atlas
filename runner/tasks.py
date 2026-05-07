from __future__ import annotations

from celery import shared_task

from .runner import _run_job


@shared_task(bind=True, name="runner.run_job")
def run_job_task(self, job_id: int) -> None:
    _run_job(job_id)

