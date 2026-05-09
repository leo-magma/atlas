from __future__ import annotations

import base64
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "suiteui.settings")
# Dash/Flask callbacks can run while an event loop is active in modern Dash installs.
# The UI is a local single-user runner, and the long-running job itself is still moved
# to a worker thread/Celery by runner.start_job_async.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

import django

django.setup()

from dash import ALL, Dash, Input, Output, State, dcc, html, no_update
from dash import callback_context as ctx
from django.conf import settings
from django.core.management import call_command
from flask import Response, redirect, send_file, session

from runner.forms import (
    EXTRA_EXTENSIONS,
    MAX_EXTRA_FILE_SIZE,
    MAX_EXTRA_FILES,
    MAX_EXTRA_TOTAL_SIZE,
    MAX_SCRIPT_SIZE,
    SCRIPT_EXTENSIONS,
)
from runner.models import RunJob
from runner.runner import start_job_async

BASE_DIR = Path(__file__).resolve().parents[1]
DSL_ORDER = ["atlas", "neptune", "hydra", "chronos", "athena"]
DSL_LABELS = {
    "atlas": "Equity",
    "neptune": "Fixed Income",
    "hydra": "Derivatives",
    "chronos": "Time Series",
    "athena": "Machine Learning",
}
DSL_DESCRIPTIONS = {
    "atlas": "Risk scripting: returns, volatility, VaR/ES, corr/cov, beta, Sharpe, drawdown, diagnostics.",
    "neptune": "Fixed-income analytics: curve/bond loaders, YTM, duration, convexity, DV01, z-spread.",
    "hydra": "Options analytics: Black-Scholes pricing, Greeks, implied volatility, vol-surface checks.",
    "chronos": "Time-series ETL: load, clean, join, resample, shift, diff, normalize, validation.",
    "athena": "ML orchestration: features, train, predict, evaluate, backtest, model IO.",
}
DESK_LABELS = {
    "atlas": "Equity Risk",
    "neptune": "Fixed Income Analytics",
    "hydra": "Derivatives Pricing",
    "chronos": "Time-Series Data Quality",
    "athena": "ML Research Workflow",
}
CONTROL_LABELS = {
    "atlas": "VaR / ES / Drawdown / Beta",
    "neptune": "YTM / Duration / DV01 / Z-Spread",
    "hydra": "BS Price / Greeks / Implied Vol",
    "chronos": "Schema / Frequency / Missingness",
    "athena": "Features / Backtest / Reproducibility",
}
GOVERNANCE_LABELS = {
    "atlas": ["Risk metric validation", "Backtest-ready diagnostics", "Input/output audit"],
    "neptune": ["Curve consistency", "Solver failure handling", "Sensitivity review"],
    "hydra": ["No-arbitrage checks", "IV solver controls", "Greek exposure review"],
    "chronos": ["Schema validation", "Frequency integrity", "Missingness controls"],
    "athena": ["Leakage control", "Seeded reproducibility", "Walk-forward validation"],
}
READINESS_LABELS = [
    ("Scope", "Five finance DSL runtimes"),
    ("Controls", "Validation and diagnostics visible"),
    ("Auditability", "Inputs, outputs, errors, and timing tracked"),
    ("Operability", "Upload, run, cancel, edit, rerun"),
]


def _ensure_db() -> None:
    call_command("migrate", interactive=False, verbosity=0)


def _safe_name(name: str) -> str:
    p = Path(name)
    if not p.name or p.name != name or "/" in name or "\\" in name:
        raise ValueError("filename must not contain path separators")
    return p.name


def _parse_upload(content: str) -> bytes:
    if not content or "," not in content:
        raise ValueError("invalid upload payload")
    _, encoded = content.split(",", 1)
    return base64.b64decode(encoded)


def _decode_uploads(contents: Any, filenames: Any) -> list[tuple[str, bytes]]:
    if not contents:
        return []
    if not isinstance(contents, list):
        contents = [contents]
    if not isinstance(filenames, list):
        filenames = [filenames]
    return [(_safe_name(str(name)), _parse_upload(str(body))) for name, body in zip(filenames, contents, strict=True)]


def _session_job_ids() -> set[int]:
    raw = session.get("suiteui_job_ids", [])
    try:
        return {int(x) for x in raw}
    except Exception:
        return set()


def _remember_job(job: RunJob) -> None:
    session["suiteui_job_ids"] = sorted(_session_job_ids() | {int(job.id)})
    session.modified = True


def _can_access_job(job: RunJob) -> bool:
    if not settings.SUITEUI_REQUIRE_JOB_SESSION:
        return True
    return int(job.id) in _session_job_ids()


def _get_job(job_id: int) -> RunJob | None:
    try:
        job = RunJob.objects.get(id=job_id)
    except RunJob.DoesNotExist:
        return None
    return job if _can_access_job(job) else None


def _safe_manifest(job: RunJob) -> list[str]:
    allowed_exts = {".atl", ".chr", ".hyd", ".nep", ".ath", *EXTRA_EXTENSIONS}
    try:
        raw = json.loads(job.input_manifest or "[]")
    except Exception:
        raw = []
    script_name = Path(job.uploaded_file.path).name
    out = []
    for name in raw:
        p = Path(str(name))
        if p.name == str(name) and p.name and p.suffix.lower() in allowed_exts:
            out.append(p.name)
    job_dir = Path(job.uploaded_file.path).parent
    if job_dir.exists():
        for p in sorted(job_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in allowed_exts:
                out.append(p.name)
    merged = [script_name, *[name for name in out if name != script_name]]
    return list(dict.fromkeys(merged)) or [script_name]


def _input_target(job: RunJob, name: str) -> Path:
    if Path(name).name != name or name not in _safe_manifest(job):
        raise ValueError("input file is not available for this job")
    target = (Path(job.uploaded_file.path).parent / name).resolve()
    job_dir = Path(job.uploaded_file.path).parent.resolve()
    if not target.is_relative_to(job_dir) or not target.exists() or not target.is_file():
        raise ValueError("input file not found")
    if target.suffix.lower() not in {".atl", ".chr", ".hyd", ".nep", ".ath", *EXTRA_EXTENSIONS}:
        raise ValueError("unsupported input file type")
    return target


def _save_input_text(job: RunJob, name: str, text: str) -> None:
    target = _input_target(job, name)
    if len(text.encode("utf-8")) > 1_000_000:
        raise ValueError("edited file is too large (max 1MB)")
    target.write_text(text, encoding="utf-8")


def _read_input_text(job: RunJob, name: str) -> str:
    target = _input_target(job, name)
    text = target.read_text(encoding="utf-8", errors="replace")
    return text[:200_000] + ("\n\n... (truncated) ..." if len(text) > 200_000 else "")


def _rerun_job(job: RunJob) -> None:
    if job.status in {"queued", "running"}:
        raise ValueError("job is already running")
    job.status = "queued"
    job.progress = 0
    job.started_at = None
    job.finished_at = None
    job.output_text = ""
    job.error_text = ""
    job.cancel_requested = False
    job.save(
        update_fields=[
            "status",
            "progress",
            "started_at",
            "finished_at",
            "output_text",
            "error_text",
            "cancel_requested",
        ]
    )
    start_job_async(job.id)


def _example_dir(dsl: str) -> Path:
    return BASE_DIR / "examples" if dsl == "atlas" else BASE_DIR / dsl / "examples"


def _example_files(dsl: str) -> list[Path]:
    root = _example_dir(dsl)
    if not root.exists():
        return []
    suffix = SCRIPT_EXTENSIONS.get(dsl)
    return sorted(p for p in root.glob("*.*") if p.is_file() and p.suffix.lower() == suffix)


def _validate_uploads(dsl: str, script: tuple[str, bytes], extras: list[tuple[str, bytes]]) -> None:
    script_name, script_bytes = script
    expected = SCRIPT_EXTENSIONS[dsl]
    if Path(script_name).suffix.lower() != expected:
        raise ValueError(f"{dsl} scripts must use the {expected} extension.")
    if len(script_bytes) > MAX_SCRIPT_SIZE:
        raise ValueError("script file too large (max 5MB)")
    if len(extras) > MAX_EXTRA_FILES:
        raise ValueError(f"too many data files (max {MAX_EXTRA_FILES})")
    total = 0
    for name, body in extras:
        total += len(body)
        if len(body) > MAX_EXTRA_FILE_SIZE:
            raise ValueError(f"{name}: file too large (max 10MB)")
        if Path(name).suffix.lower() not in EXTRA_EXTENSIONS:
            allowed = ", ".join(sorted(EXTRA_EXTENSIONS))
            raise ValueError(f"{name}: unsupported data file type. Allowed: {allowed}.")
    if total > MAX_EXTRA_TOTAL_SIZE:
        raise ValueError("data files too large (total max 20MB)")


def _create_uploaded_job(dsl: str, script: tuple[str, bytes], extras: list[tuple[str, bytes]]) -> RunJob:
    _validate_uploads(dsl, script, extras)
    date_part = datetime.utcnow().strftime("%Y%m%d")
    job_dir = Path(settings.MEDIA_ROOT) / "uploads" / date_part / uuid.uuid4().hex[:12]
    job_dir.mkdir(parents=True, exist_ok=True)

    script_name, script_bytes = script
    script_path = job_dir / script_name
    script_path.write_bytes(script_bytes)
    manifest = [script_name]

    for name, body in extras:
        (job_dir / name).write_bytes(body)
        manifest.append(name)

    rel = script_path.relative_to(settings.MEDIA_ROOT).as_posix()
    job = RunJob.objects.create(dsl=dsl, uploaded_file=rel, input_manifest=json.dumps(sorted(set(manifest))))
    _remember_job(job)
    start_job_async(job.id)
    return job


def _create_example_job(dsl: str, name: str) -> RunJob:
    name = _safe_name(name)
    examples = _example_dir(dsl).resolve()
    candidate = (examples / name).resolve()
    if examples not in candidate.parents or not candidate.exists():
        raise ValueError("example not found")

    dst_dir = Path(settings.MEDIA_ROOT) / "examples" / dsl / uuid.uuid4().hex[:12]
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / candidate.name
    dst.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
    manifest = [dst.name]

    for p in examples.glob("*"):
        if p.is_file() and p.name != name and p.suffix.lower() in EXTRA_EXTENSIONS:
            shutil.copy2(p, dst_dir / p.name)
            manifest.append(p.name)

    rel = dst.relative_to(settings.MEDIA_ROOT).as_posix()
    job = RunJob.objects.create(dsl=dsl, uploaded_file=rel, input_manifest=json.dumps(sorted(set(manifest))))
    _remember_job(job)
    start_job_async(job.id)
    return job


def _jobs_for_dsl(dsl: str, q: str = "") -> list[RunJob]:
    qs = RunJob.objects.filter(dsl=dsl)
    if settings.SUITEUI_REQUIRE_JOB_SESSION:
        qs = qs.filter(id__in=_session_job_ids())
    if q:
        qs = qs.filter(uploaded_file__icontains=q)
    return list(qs[:25])


def _visible_jobs(dsl: str | None = None) -> list[RunJob]:
    qs = RunJob.objects.all()
    if dsl is not None:
        qs = qs.filter(dsl=dsl)
    if settings.SUITEUI_REQUIRE_JOB_SESSION:
        qs = qs.filter(id__in=_session_job_ids())
    return list(qs[:100])


def _job_counts() -> dict[str, int]:
    ids = _session_job_ids() if settings.SUITEUI_REQUIRE_JOB_SESSION else None
    out: dict[str, int] = {}
    for dsl in DSL_ORDER:
        qs = RunJob.objects.filter(dsl=dsl)
        if ids is not None:
            qs = qs.filter(id__in=ids)
        out[dsl] = int(qs.count())
    return out


def _status_summary(dsl: str | None = None) -> dict[str, float]:
    jobs = _visible_jobs(dsl)
    total = len(jobs)
    succeeded = sum(1 for job in jobs if job.status == "succeeded")
    failed = sum(1 for job in jobs if job.status == "failed")
    active = sum(1 for job in jobs if job.status in {"queued", "running"})
    success_rate = (succeeded / total * 100.0) if total else 0.0
    return {
        "total": float(total),
        "succeeded": float(succeeded),
        "failed": float(failed),
        "active": float(active),
        "success_rate": success_rate,
    }


def _format_dt(value: Any) -> str:
    if not value:
        return "-"
    try:
        return value.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)


def _short_path(value: str, max_len: int = 58) -> str:
    if len(value) <= max_len:
        return value
    return "..." + value[-(max_len - 3):]


def _status_label(status: str) -> str:
    return {
        "queued": "QUEUED",
        "running": "RUNNING",
        "succeeded": "OK",
        "failed": "BREACH",
        "cancelled": "CANCELLED",
    }.get(status, status.upper())


def _governance_cards(dsl: str) -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div(f"CONTROL {i}", className="terminal-label"),
                    html.Div(label, className="terminal-value governance-value"),
                    html.Div("MONITORED", className="control-badge"),
                ],
                className="terminal-tile governance-card",
            )
            for i, label in enumerate(GOVERNANCE_LABELS[dsl], start=1)
        ],
        className="governance-grid",
    )


def _job_audit_summary(job: RunJob) -> dict[str, str]:
    inputs = _safe_manifest(job)
    output_chars = len(job.output_text or "")
    error_chars = len(job.error_text or "")
    started = _format_dt(job.started_at)
    finished = _format_dt(job.finished_at)
    return {
        "inputs": str(len(inputs)),
        "output": f"{output_chars:,} chars",
        "errors": f"{error_chars:,} chars",
        "started": started,
        "finished": finished,
    }


def _readiness_panel() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div(label, className="terminal-label"),
                    html.Div(value, className="terminal-value readiness-value"),
                    html.Div("VP DEMO READY", className="control-badge readiness-badge"),
                ],
                className="terminal-tile readiness-card",
            )
            for label, value in READINESS_LABELS
        ],
        className="readiness-grid",
    )


def _sidebar(active: str) -> html.Aside:
    logo = active if active in [*DSL_ORDER, "overview"] else "overview"
    items = [
        html.A(
            [html.Span(className="dot overview-dot"), html.Span("Overview", className="label")],
            href="/overview",
            className=f"nav-item {'active' if active == 'overview' else ''}",
        )
    ]
    for dsl in DSL_ORDER:
        items.append(
            html.A(
                [html.Span(className="dot"), html.Span(DSL_LABELS[dsl], className="label")],
                href=f"/dsl/{dsl}",
                className=f"nav-item {'active' if active == dsl else ''}",
            )
        )
    return html.Aside(
        [
            html.Div([html.Div("Atlas", className="brand-title"), html.Div("Runner UI (Dash)", className="brand-sub")]),
            html.Nav(items, className="nav"),
            html.Div(
                [
                    html.Div(
                        html.Img(src=f"/assets/images/logos/{logo}.svg", className="sidebar-logo"),
                        className="sidebar-logo-stage",
                    ),
                    html.Div("Dark UI + blue accents", className="muted"),
                ],
                className="sidebar-footer",
            ),
        ],
        className="sidebar",
    )


def _shell(content: Any, active: str) -> html.Div:
    return html.Div([_sidebar(active), html.Main(content, className="main")], className="layout")


def _overview_layout() -> html.Div:
    counts = _job_counts()
    summary = _status_summary()
    cards = [
        html.Div(
            [
                html.Div(DESK_LABELS[dsl], className="terminal-label"),
                html.Div(f"{DSL_LABELS[dsl]} ({SCRIPT_EXTENSIONS[dsl]})", className="mono terminal-value"),
                html.Div(CONTROL_LABELS[dsl], className="muted small"),
                html.Div(f"{counts[dsl]} runs", className="desk-count"),
            ],
            className="example-item desk-card",
        )
        for dsl in DSL_ORDER
    ]
    content = [
        html.Header([html.Div([html.H1("Multi-Asset Risk & Analytics Console", className="h1"), html.Div("Atlas — execution, validation, and inspection layer for finance-focused DSL workflows.", className="sub")])], className="header"),
        html.Section(
            [
                html.H2("Control Room", className="h2"),
                html.Div(
                    [
                        html.Div([html.Div("Coverage", className="terminal-label"), html.Div("Equity / FI / Derivatives / Time-Series / ML", className="terminal-value")], className="terminal-tile wide"),
                        html.Div([html.Div("Execution", className="terminal-label"), html.Div("Upload / Run / Edit / Rerun", className="terminal-value")], className="terminal-tile"),
                        html.Div([html.Div("Audit", className="terminal-label"), html.Div("Inputs / Output / Error", className="terminal-value")], className="terminal-tile"),
                    ],
                    className="terminal-strip overview-strip",
                ),
                html.Div(
                    [
                        html.Div([html.Div("Total Runs", className="terminal-label"), html.Div(f"{summary['total']:.0f}", className="terminal-value")], className="terminal-tile metric-tile"),
                        html.Div([html.Div("Success Rate", className="terminal-label"), html.Div(f"{summary['success_rate']:.1f}%", className="terminal-value")], className="terminal-tile metric-tile"),
                        html.Div([html.Div("Active", className="terminal-label"), html.Div(f"{summary['active']:.0f}", className="terminal-value")], className="terminal-tile metric-tile"),
                        html.Div([html.Div("Failed", className="terminal-label"), html.Div(f"{summary['failed']:.0f}", className="terminal-value")], className="terminal-tile metric-tile danger-metric"),
                    ],
                    className="kpi-grid",
                ),
                html.Div("Atlas is a collection of sibling DSL runtimes focused on quantitative finance workflows. Each DSL executes a pipeline of named steps such as load, transform, compute, and print.", className="muted"),
            ],
            className="card",
        ),
        html.Section(
            [
                html.Div([html.H2("Languages", className="h2"), html.Div(cards, className="examples")], className="card"),
                html.Div(
                    [
                        html.H2("How to use", className="h2"),
                        html.Div(
                            [
                                html.Div([html.Div("1) Upload", className="mono"), html.Div("Upload a script and optional CSV/data files referenced by load.", className="muted small")], className="example-item"),
                                html.Div([html.Div("2) Run", className="mono"), html.Div("Jobs start immediately in a local background thread by default.", className="muted small")], className="example-item"),
                                html.Div([html.Div("3) Inspect", className="mono"), html.Div("Open a job to view progress, output, errors, and used inputs.", className="muted small")], className="example-item"),
                            ],
                            className="examples",
                        ),
                    ],
                    className="card",
                ),
            ],
            className="grid",
        ),
        html.Section(
            [
                html.H2("Executive Readiness", className="h2"),
                _readiness_panel(),
            ],
            className="card readiness-section",
        ),
    ]
    return _shell(content, "overview")


def _upload_box(text: str, component_id: str, multiple: bool) -> dcc.Upload:
    return dcc.Upload(
        id=component_id,
        multiple=multiple,
        children=html.Div(text, className="btn secondary"),
        style={"display": "inline-flex"},
    )


def _job_rows(jobs: list[RunJob]) -> list[Any]:
    rows: list[Any] = [
        html.Div([html.Div("ID"), html.Div("File"), html.Div("Status"), html.Div("Progress"), html.Div("Created"), html.Div("")], className="table-head")
    ]
    if not jobs:
        rows.append(html.Div("No jobs yet.", className="muted"))
        return rows
    for job in jobs:
        rows.append(
            html.Div(
                [
                    html.Div(f"#{job.id}"),
                    html.Div(_short_path(job.uploaded_file.name), className="mono small", title=job.uploaded_file.name),
                    html.Div(html.Span(_status_label(job.status), className=f"pill {job.status}")),
                    html.Div(f"{job.progress}%", className="mono"),
                    html.Div(_format_dt(job.created_at), className="muted"),
                    html.Div(html.A("Open", href=f"/job/{job.id}", className="link")),
                ],
                className="table-row",
            )
        )
    return rows


def _dsl_layout(dsl: str, q: str = "") -> html.Div:
    if dsl not in DSL_ORDER:
        dsl = "atlas"
    examples = _example_files(dsl)
    summary = _status_summary(dsl)
    content = [
        dcc.Store(id="current-dsl", data=dsl),
        html.Header(
            [
                html.Div(
                    [
                        html.H1(f"{DESK_LABELS[dsl]}", className="h1"),
                        html.Div(f"{CONTROL_LABELS[dsl]} — upload, execute, inspect, edit, and rerun.", className="sub"),
                    ]
                )
            ],
            className="header",
        ),
        html.Section(
            [
                html.Div(
                    [
                        html.Div([html.Div("DESK", className="terminal-label"), html.Div(DESK_LABELS[dsl], className="terminal-value")], className="terminal-tile"),
                        html.Div([html.Div("CONTROL", className="terminal-label"), html.Div(CONTROL_LABELS[dsl], className="terminal-value")], className="terminal-tile wide"),
                        html.Div([html.Div("EXT", className="terminal-label"), html.Div(SCRIPT_EXTENSIONS[dsl], className="terminal-value")], className="terminal-tile"),
                        html.Div([html.Div("RUNTIME", className="terminal-label"), html.Div("LOCAL / ASYNC READY", className="terminal-value")], className="terminal-tile"),
                    ],
                    className="terminal-strip",
                ),
                html.Div(
                    [
                        html.Div([html.Div("Runs", className="terminal-label"), html.Div(f"{summary['total']:.0f}", className="terminal-value")], className="terminal-tile metric-tile"),
                        html.Div([html.Div("Success", className="terminal-label"), html.Div(f"{summary['success_rate']:.1f}%", className="terminal-value")], className="terminal-tile metric-tile"),
                        html.Div([html.Div("Active", className="terminal-label"), html.Div(f"{summary['active']:.0f}", className="terminal-value")], className="terminal-tile metric-tile"),
                        html.Div([html.Div("Failed", className="terminal-label"), html.Div(f"{summary['failed']:.0f}", className="terminal-value")], className="terminal-tile metric-tile danger-metric"),
                    ],
                    className="kpi-grid",
                ),
                html.H2("Control Framework", className="h2"),
                _governance_cards(dsl),
            ],
            className="card",
        ),
        html.Section(
            [
                html.H2("Run a script", className="h2"),
                html.Div(
                    [
                        html.Div([html.Label("Script file"), _upload_box("Choose script", "script-upload", False), html.Div(id="script-upload-name", className="muted small")], className="field grow"),
                        html.Div([html.Label("Data files"), _upload_box("Choose data files", "data-upload", True), html.Div(id="data-upload-name", className="muted small")], className="field grow"),
                        html.Div([html.Label(""), html.Button("Run", id="run-upload", className="btn")], className="field"),
                    ],
                    className="row",
                ),
                html.Pre(id="run-message", className="error"),
            ],
            className="card",
        ),
        html.Section(
            [
                html.Div(
                    [
                        html.H2("Recent jobs", className="h2"),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Label("Search"),
                                        dcc.Input(
                                            id="job-search",
                                            value=q,
                                            placeholder="filter by filename...",
                                            className="search-input",
                                        ),
                                    ],
                                    className="field grow",
                                ),
                                html.Div(
                                    [html.Label(""), html.Button("Apply", id="search-apply", className="btn secondary")],
                                    className="field",
                                ),
                            ],
                            className="row search-row",
                        ),
                        html.Div(id="job-table", className="table", children=_job_rows(_jobs_for_dsl(dsl, q))),
                    ],
                    className="card",
                ),
                html.Div(
                    [
                        html.H2("Examples", className="h2"),
                        html.Div("Run examples with one click.", className="muted"),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(ex.name, className="mono grow"),
                                        html.Button("Run", id={"type": "run-example", "dsl": dsl, "name": ex.name}, className="btn secondary"),
                                        html.Div(str(ex), className="muted small"),
                                    ],
                                    className="example-item",
                                )
                                for ex in examples
                            ]
                            or [html.Div("No examples found.", className="muted")],
                            className="examples",
                        ),
                    ],
                    className="card",
                ),
            ],
            className="grid",
        ),
        dcc.Interval(id="dsl-refresh", interval=700, n_intervals=0),
    ]
    return _shell(content, dsl)


def _job_layout(job_id: int) -> html.Div:
    job = _get_job(job_id)
    if job is None:
        return _shell(html.Section([html.H1("Job not found", className="h1"), html.Div("This job is not available in the current session.", className="error")], className="card"), "overview")
    inputs = _safe_manifest(job)
    script_name = Path(job.uploaded_file.path).name
    try:
        initial_input_text = _read_input_text(job, script_name)
    except Exception:
        initial_input_text = ""
    audit = _job_audit_summary(job)
    content = [
        dcc.Store(id="current-job-id", data=job.id),
        dcc.Store(id="current-script-name", data=script_name),
        html.Header(
            [
                html.Div([html.H1(f"Job #{job.id} — {DESK_LABELS.get(job.dsl, job.dsl)}", className="h1"), html.Div(job.uploaded_file.name, className="mono muted small"), html.Div(f"{CONTROL_LABELS.get(job.dsl, 'Execution')} with live status, inputs, output, and error inspection.", className="sub")]),
                html.Div([html.A("Back", href=f"/dsl/{job.dsl}", className="btn secondary"), html.Button("Cancel", id="cancel-job", className="btn secondary danger"), html.A("Download output", href=f"/download/{job.id}/output", className="btn secondary"), html.A("Download error", href=f"/download/{job.id}/error", className="btn secondary")], className="header-actions"),
            ],
            className="header",
        ),
        html.Section(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("RUN ID", className="terminal-label"),
                                html.Div(f"#{job.id}", className="terminal-value"),
                            ],
                            className="terminal-tile",
                        ),
                        html.Div(
                            [
                                html.Div("LANGUAGE", className="terminal-label"),
                                html.Div(DSL_LABELS.get(job.dsl, job.dsl), className="terminal-value"),
                            ],
                            className="terminal-tile",
                        ),
                        html.Div(
                            [
                                html.Div("SCRIPT", className="terminal-label"),
                                html.Div(script_name, className="terminal-value mono"),
                            ],
                            className="terminal-tile wide",
                        ),
                        html.Div(
                            [
                                html.Div("MODE", className="terminal-label"),
                                html.Div("LOCAL EXEC", className="terminal-value"),
                            ],
                            className="terminal-tile",
                        ),
                    ],
                    className="terminal-strip",
                ),
                html.Div(
                    [
                        html.Div([html.Div("Inputs", className="terminal-label"), html.Div(audit["inputs"], className="terminal-value")], className="terminal-tile metric-tile"),
                        html.Div([html.Div("Output", className="terminal-label"), html.Div(audit["output"], className="terminal-value")], className="terminal-tile metric-tile"),
                        html.Div([html.Div("Errors", className="terminal-label"), html.Div(audit["errors"], className="terminal-value")], className="terminal-tile metric-tile danger-metric"),
                        html.Div([html.Div("Started", className="terminal-label"), html.Div(audit["started"], className="terminal-value")], className="terminal-tile metric-tile"),
                        html.Div([html.Div("Finished", className="terminal-label"), html.Div(audit["finished"], className="terminal-value")], className="terminal-tile metric-tile"),
                    ],
                    className="job-audit-grid",
                ),
                html.Div(
                    [
                        html.Div([html.Div("Status", className="muted small"), html.Div(_status_label(job.status), id="status-pill", className=f"pill {job.status}")], className="field grow"),
                        html.Div([html.Div("Progress", className="muted small"), html.Div(html.Div(id="progress-bar", className="progress-bar", style={"width": f"{job.progress}%"}), className="progress"), html.Div(f"{job.progress}%", id="progress-text", className="mono small")], className="field grow"),
                    ],
                    className="row",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H2("Inputs", className="h2"),
                                dcc.Dropdown(
                                    id="input-select",
                                    options=[{"label": x, "value": x} for x in inputs],
                                    value=script_name,
                                    clearable=False,
                                ),
                                html.Div(
                                    [
                                        html.Button(
                                            "Edit run script",
                                            id="select-script",
                                            className="btn secondary",
                                            type="button",
                                        ),
                                        html.Button(
                                            "Save input",
                                            id="save-input",
                                            className="btn secondary",
                                            type="button",
                                        ),
                                        html.Button(
                                            "Save & rerun",
                                            id="rerun-edited",
                                            className="btn",
                                            type="button",
                                        ),
                                        html.Span(id="input-save-message", className="muted small"),
                                    ],
                                    className="row input-actions",
                                    style={"marginTop": "10px"},
                                ),
                                dcc.Textarea(
                                    id="input-text",
                                    className="log log-flex input-editor",
                                    value=initial_input_text,
                                    spellCheck=False,
                                ),
                            ],
                            className="pane pane-left",
                        ),
                        html.Div([html.H2("Output", className="h2"), html.Pre(job.output_text, id="out", className="log log-flex"), html.H2("Error", className="h2", style={"marginTop": "10px"}), html.Pre(job.error_text, id="err", className="log log-error error")], className="pane pane-right"),
                    ],
                    className="jobgrid",
                ),
            ],
            className="card",
        ),
        dcc.Interval(id="job-refresh", interval=800, n_intervals=0),
    ]
    return _shell(content, job.dsl)


_ensure_db()
app = Dash(__name__, assets_folder=str(BASE_DIR / "static"), suppress_callback_exceptions=True)
server = app.server
server.secret_key = settings.SECRET_KEY
app.title = "Atlas UI"
app.index_string = """<!DOCTYPE html>
<html>
  <head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}</head>
  <body class="app">{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>"""
app.layout = html.Div([dcc.Location(id="url"), html.Div(id="page")])


@server.route("/")
def root_redirect():
    return redirect("/dsl/atlas")


@server.route("/download/<int:job_id>/<kind>")
def download(job_id: int, kind: str):
    job = _get_job(job_id)
    if job is None:
        return Response("Forbidden", status=403)
    if kind not in {"output", "error"}:
        return Response("Unsupported", status=415)
    text = job.output_text if kind == "output" else job.error_text
    return Response(
        text,
        headers={"Content-Disposition": f'attachment; filename="job_{job.id}_{kind}.txt"'},
        mimetype="text/plain; charset=utf-8",
    )


@app.callback(Output("page", "children"), Input("url", "pathname"), State("url", "search"))
def render_page(pathname: str | None, search: str | None):
    path = pathname or "/dsl/atlas"
    if path == "/overview":
        return _overview_layout()
    if path.startswith("/job/"):
        try:
            return _job_layout(int(path.strip("/").split("/")[-1]))
        except ValueError:
            return _overview_layout()
    if path.startswith("/dsl/"):
        dsl = path.strip("/").split("/")[-1]
        q = ""
        if search and search.startswith("?q="):
            q = search[3:]
        return _dsl_layout(dsl, q)
    return _dsl_layout("atlas")


@app.callback(
    Output("script-upload-name", "children"),
    Input("script-upload", "filename"),
    prevent_initial_call=True,
)
def show_script_name(filename: str | None):
    return filename or ""


@app.callback(
    Output("data-upload-name", "children"),
    Input("data-upload", "filename"),
    prevent_initial_call=True,
)
def show_data_names(filenames: Any):
    if not filenames:
        return ""
    return ", ".join(filenames if isinstance(filenames, list) else [filenames])


@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("run-message", "children"),
    Input("run-upload", "n_clicks"),
    Input({"type": "run-example", "dsl": ALL, "name": ALL}, "n_clicks"),
    State("current-dsl", "data"),
    State("script-upload", "contents"),
    State("script-upload", "filename"),
    State("data-upload", "contents"),
    State("data-upload", "filename"),
    prevent_initial_call=True,
)
def run_action(_upload_clicks: int | None, _example_clicks: list[int] | None, dsl: str, script_content: str | None, script_name: str | None, data_contents: Any, data_names: Any):
    trig = ctx.triggered_id
    try:
        if trig == "run-upload":
            script_files = _decode_uploads(script_content, script_name)
            if len(script_files) != 1:
                raise ValueError("choose exactly one script file")
            job = _create_uploaded_job(dsl, script_files[0], _decode_uploads(data_contents, data_names))
            return f"/job/{job.id}", ""
        if isinstance(trig, dict) and trig.get("type") == "run-example":
            job = _create_example_job(trig["dsl"], trig["name"])
            return f"/job/{job.id}", ""
    except Exception as exc:
        return no_update, str(exc)
    return no_update, ""


@app.callback(
    Output("job-table", "children"),
    Input("dsl-refresh", "n_intervals"),
    Input("search-apply", "n_clicks"),
    State("current-dsl", "data"),
    State("job-search", "value"),
)
def refresh_job_table(_n: int, _clicks: int | None, dsl: str, q: str | None):
    return _job_rows(_jobs_for_dsl(dsl, q or ""))


@app.callback(
    Output("status-pill", "children"),
    Output("status-pill", "className"),
    Output("progress-bar", "style"),
    Output("progress-text", "children"),
    Output("out", "children"),
    Output("err", "children"),
    Output("input-select", "options"),
    Input("job-refresh", "n_intervals"),
    Input("cancel-job", "n_clicks"),
    State("current-job-id", "data"),
)
def refresh_job(_n: int, cancel_clicks: int | None, job_id: int):
    job = _get_job(int(job_id))
    if job is None:
        return "forbidden", "pill failed", {"width": "100%"}, "100%", "", "Forbidden", []
    if ctx.triggered_id == "cancel-job" and cancel_clicks and job.status not in {"succeeded", "failed", "cancelled"}:
        job.cancel_requested = True
        job.save(update_fields=["cancel_requested"])
        job.refresh_from_db()
    return (
        _status_label(job.status),
        f"pill {job.status}",
        {"width": f"{job.progress}%"},
        f"{job.progress}%",
        job.output_text,
        job.error_text,
        [{"label": x, "value": x} for x in _safe_manifest(job)],
    )


@app.callback(
    Output("input-select", "value"),
    Input("select-script", "n_clicks"),
    State("current-script-name", "data"),
    prevent_initial_call=True,
)
def select_run_script(_clicks: int | None, script_name: str):
    return script_name


@app.callback(
    Output("input-text", "value"),
    Input("input-select", "value"),
    State("current-job-id", "data"),
)
def load_input(name: str | None, job_id: int):
    if not name:
        return ""
    job = _get_job(int(job_id))
    if job is None:
        return "Forbidden"
    try:
        return _read_input_text(job, name)
    except ValueError as exc:
        return str(exc)


@app.callback(
    Output("input-save-message", "children"),
    Input("save-input", "n_clicks"),
    Input("rerun-edited", "n_clicks"),
    State("current-job-id", "data"),
    State("input-select", "value"),
    State("input-text", "value"),
    prevent_initial_call=True,
)
def save_or_rerun_input(
    _save_clicks: int | None,
    _rerun_clicks: int | None,
    job_id: int,
    name: str | None,
    text: str | None,
):
    if not name:
        return "No input file selected."
    job = _get_job(int(job_id))
    if job is None:
        return "Forbidden."
    try:
        _save_input_text(job, name, text or "")
        if ctx.triggered_id == "rerun-edited":
            _rerun_job(job)
            return "Saved and rerun started."
        return "Saved."
    except Exception as exc:
        return str(exc)


def main() -> None:
    host = os.environ.get("DASH_HOST", "127.0.0.1")
    port = int(os.environ.get("DASH_PORT", "8000"))
    app.run(host=host, port=port, debug=settings.DEBUG)


if __name__ == "__main__":
    main()
