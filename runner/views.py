from __future__ import annotations

import json
from pathlib import Path
import shutil

from django.conf import settings
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EXTRA_EXTENSIONS, UploadRunForm
from .models import RunJob
from .runner import start_job_async


DSL_ORDER = ["atlas", "neptune", "hydra", "chronos", "athena"]


def _session_job_ids(request) -> set[int]:
    raw = request.session.get("suiteui_job_ids", [])
    try:
        return {int(x) for x in raw}
    except Exception:
        return set()


def _remember_job(request, job: RunJob) -> None:
    ids = sorted(_session_job_ids(request) | {int(job.id)})
    request.session["suiteui_job_ids"] = ids
    request.session.modified = True


def _can_access_job(request, job: RunJob) -> bool:
    if not settings.SUITEUI_REQUIRE_JOB_SESSION:
        return True
    return int(job.id) in _session_job_ids(request)


def _get_accessible_job(request, job_id: int) -> RunJob | None:
    job = get_object_or_404(RunJob, id=job_id)
    if not _can_access_job(request, job):
        return None
    return job


def _safe_manifest(files: list[str], fallback: str) -> list[str]:
    safe = []
    for name in files:
        p = Path(str(name))
        if p.name == str(name) and p.name:
            safe.append(p.name)
    return safe or [Path(fallback).name]


def home(request):
    return redirect("dsl_page", dsl="atlas")


def overview(request):
    ctx = {"dsl_order": DSL_ORDER, "active_tab": "overview"}
    return render(request, "runner/overview.html", ctx)


def dsl_page(request, dsl: str):
    dsl = dsl.lower()
    if dsl not in {c[0] for c in RunJob.DSL_CHOICES}:
        return redirect("dsl_page", dsl="atlas")

    if request.method == "POST":
        form = UploadRunForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save()
            # Copy uploaded "extra files" next to the script so relative loads work.
            extra = form.cleaned_data.get("extra_files") or []
            job_dir = Path(job.uploaded_file.path).parent
            manifest = [Path(job.uploaded_file.path).name]
            for f in extra:
                dst = job_dir / Path(f.name).name
                with open(dst, "wb") as out:
                    for chunk in f.chunks():
                        out.write(chunk)
                manifest.append(dst.name)
            job.input_manifest = json.dumps(sorted(set(manifest)))
            job.save(update_fields=["input_manifest"])
            _remember_job(request, job)
            start_job_async(job.id)
            return redirect("job_detail", job_id=job.id)
    else:
        form = UploadRunForm(initial={"dsl": dsl})

    q = (request.GET.get("q") or "").strip()
    jobs_qs = RunJob.objects.filter(dsl=dsl)
    if settings.SUITEUI_REQUIRE_JOB_SESSION:
        jobs_qs = jobs_qs.filter(id__in=_session_job_ids(request))
    if q:
        jobs_qs = jobs_qs.filter(uploaded_file__icontains=q)
    jobs = jobs_qs[:25]

    # Show examples from repo folders if present
    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / (dsl if dsl != "atlas" else "examples")
    # atlas examples live in /examples; others in /<dsl>/examples
    if dsl != "atlas":
        examples_dir = repo_root / dsl / "examples"

    example_files = []
    if examples_dir.exists():
        for p in sorted(examples_dir.glob("*.*")):
            if p.suffix.lower() in (".atl", ".chr", ".hyd", ".nep", ".ath"):
                example_files.append({"name": p.name, "path": str(p)})

    ctx = {
        "dsl": dsl,
        "form": form,
        "jobs": jobs,
        "dsl_order": DSL_ORDER,
        "example_files": example_files,
        "q": q,
    }
    return render(request, "runner/dsl_page.html", ctx)


def job_detail(request, job_id: int):
    job = _get_accessible_job(request, job_id)
    if job is None:
        return HttpResponseForbidden("This job is not available in the current session.")
    try:
        inputs = _safe_manifest(list(json.loads(job.input_manifest or "[]")), job.uploaded_file.path)
    except Exception:
        inputs = [Path(job.uploaded_file.path).name]
    ctx = {"job": job, "dsl_order": DSL_ORDER, "input_files": inputs}
    return render(request, "runner/job_detail.html", ctx)


def job_status(request, job_id: int):
    job = _get_accessible_job(request, job_id)
    if job is None:
        return JsonResponse({"error": "forbidden"}, status=403)
    return JsonResponse(
        {
            "id": job.id,
            "dsl": job.dsl,
            "status": job.status,
            "progress": job.progress,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "output_text": job.output_text,
            "error_text": job.error_text,
        }
    )


@require_POST
def job_cancel(request, job_id: int):
    job = _get_accessible_job(request, job_id)
    if job is None:
        return HttpResponseForbidden("This job is not available in the current session.")
    if job.status in ("succeeded", "failed", "cancelled"):
        return redirect("job_detail", job_id=job.id)
    job.cancel_requested = True
    job.save(update_fields=["cancel_requested"])
    return redirect("job_detail", job_id=job.id)


def job_download(request, job_id: int, kind: str):
    job = _get_accessible_job(request, job_id)
    if job is None:
        return HttpResponseForbidden("This job is not available in the current session.")
    if kind not in ("output", "error"):
        return redirect("job_detail", job_id=job.id)
    text = job.output_text if kind == "output" else job.error_text
    resp = HttpResponse(text, content_type="text/plain; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="job_{job.id}_{kind}.txt"'
    return resp


def job_input_list(request, job_id: int):
    job = _get_accessible_job(request, job_id)
    if job is None:
        return JsonResponse({"error": "forbidden"}, status=403)
    try:
        files = _safe_manifest(list(json.loads(job.input_manifest or "[]")), job.uploaded_file.path)
    except Exception:
        files = [Path(job.uploaded_file.path).name]
    return JsonResponse({"files": files})


def job_input_file(request, job_id: int, name: str):
    job = _get_accessible_job(request, job_id)
    if job is None:
        return HttpResponseForbidden("This job is not available in the current session.")
    job_path = Path(job.uploaded_file.path)
    job_dir = job_path.parent.resolve()
    if Path(name).name != name or "/" in name or "\\" in name:
        return HttpResponse("Invalid path", status=400)

    try:
        allowed = set(_safe_manifest(list(json.loads(job.input_manifest or "[]")), job.uploaded_file.path))
    except Exception:
        allowed = {Path(job.uploaded_file.path).name}
    if name not in allowed:
        return HttpResponse("Not found", status=404)

    # Prevent path traversal
    target = (job_dir / name).resolve()
    if not target.is_relative_to(job_dir):
        return HttpResponse("Invalid path", status=400)
    if not target.exists() or not target.is_file():
        return HttpResponse("Not found", status=404)
    if target.suffix.lower() not in (".atl", ".chr", ".hyd", ".nep", ".ath", *EXTRA_EXTENSIONS):
        return HttpResponse("Unsupported", status=415)

    text = target.read_text(encoding="utf-8", errors="replace")
    # Avoid huge payloads in the browser
    if len(text) > 200_000:
        text = text[:200_000] + "\n\n... (truncated) ..."
    return HttpResponse(text, content_type="text/plain; charset=utf-8")


def run_example(request, dsl: str):
    dsl = dsl.lower()
    if request.method != "POST":
        return redirect("dsl_page", dsl=dsl)

    repo_root = Path(__file__).resolve().parents[1]
    examples_dir = repo_root / "examples" if dsl == "atlas" else repo_root / dsl / "examples"
    name = (request.POST.get("name") or "").strip()
    if not name:
        return redirect("dsl_page", dsl=dsl)

    candidate = (examples_dir / name).resolve()
    if examples_dir.resolve() not in candidate.parents:
        return redirect("dsl_page", dsl=dsl)
    if not candidate.exists():
        return redirect("dsl_page", dsl=dsl)

    # Create a job that points at a copied file in MEDIA_ROOT uploads.
    dst_dir = Path(settings.MEDIA_ROOT) / "examples" / dsl
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / name
    dst.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
    manifest = [dst.name]

    # Copy supporting assets from the example folder so relative `load "x.csv"`
    # continues to work when executed from MEDIA_ROOT.
    for p in examples_dir.glob("*"):
        if not p.is_file():
            continue
        if p.name == name:
            continue
        if p.suffix.lower() in (".csv", ".json", ".txt", ".pkl"):
            shutil.copy2(p, dst_dir / p.name)
            manifest.append(p.name)

    # Store via FileField by assigning path relative to MEDIA_ROOT.
    rel = dst.relative_to(settings.MEDIA_ROOT).as_posix()
    job = RunJob.objects.create(dsl=dsl, uploaded_file=rel)
    job.input_manifest = json.dumps(sorted(set(manifest)))
    job.save(update_fields=["input_manifest"])
    _remember_job(request, job)
    start_job_async(job.id)
    return redirect("job_detail", job_id=job.id)

