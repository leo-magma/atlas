from __future__ import annotations

import io
import sys
import os
import threading
import time
import json
import shlex
from contextlib import redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from django.db import transaction
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import RunJob


@dataclass(frozen=True)
class DslSpec:
    name: str
    ext: str
    interpreter_factory: Callable[[], object]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dsl_specs() -> dict[str, DslSpec]:
    # Imported lazily to keep import cost low for admin/migrations.
    from atlas.core import AtlasInterpreter
    from athena.core import AthenaInterpreter
    from chronos.core import ChronosInterpreter
    from hydra.core import HydraInterpreter
    from neptune.core import NeptuneInterpreter

    return {
        "atlas": DslSpec("atlas", ".atl", AtlasInterpreter),
        "neptune": DslSpec("neptune", ".nep", NeptuneInterpreter),
        "hydra": DslSpec("hydra", ".hyd", HydraInterpreter),
        "chronos": DslSpec("chronos", ".chr", ChronosInterpreter),
        "athena": DslSpec("athena", ".ath", AthenaInterpreter),
    }


def start_job_async(job_id: int) -> None:
    # Default behavior for the local UI: start immediately in a background thread.
    # To use Celery workers (distributed execution), set:
    #   $env:SUITEUI_ASYNC="1"
    use_celery = os.environ.get("SUITEUI_ASYNC", "").strip() in ("1", "true", "yes", "y")
    if use_celery:
        try:
            from .tasks import run_job_task

            run_job_task.delay(job_id)
            return
        except Exception:
            # Fall back if Celery/Redis is unavailable.
            pass

    t = threading.Thread(target=_run_job, args=(job_id,), daemon=True)
    t.start()


def _count_effective_lines(path: Path) -> int:
    n = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        n += 1
    return max(1, n)


def _discover_used_inputs(script_path: Path, job_dir: Path) -> list[str]:
    """Parse the DSL script and collect locally referenced input files.

    Heuristic: looks for quoted or unquoted tokens ending with known extensions on lines that
    contain loader verbs (load/load_curve/load_bond/load_option).
    """
    verbs = {"load", "load_curve", "load_bond", "load_option"}
    exts = {".csv", ".json", ".txt", ".pkl"}
    used = {script_path.name}

    for raw in script_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            toks = shlex.split(line, posix=True)
        except ValueError:
            continue
        if not toks:
            continue
        # Find verb token position: either "verb" directly, or after "name ="
        verb = None
        if toks[0] in verbs:
            verb = toks[0]
            rest = toks[1:]
        elif len(toks) >= 3 and toks[1] == "=" and toks[2] in verbs:
            verb = toks[2]
            rest = toks[3:]
        else:
            continue
        _ = verb
        for t in rest:
            # stop at keyword-ish tokens
            if "=" in t:
                continue
            p = Path(t.strip("\"'"))
            if p.suffix.lower() in exts and not p.is_absolute() and len(p.parts) == 1:
                candidate = (job_dir / p.name)
                if candidate.exists():
                    used.add(p.name)
    return sorted(used)


def _run_job(job_id: int) -> None:
    job = RunJob.objects.get(id=job_id)
    specs = _dsl_specs()
    spec = specs[job.dsl]

    file_path = Path(job.uploaded_file.path)
    if file_path.suffix.lower() != spec.ext:
        job.status = "failed"
        job.error_text = f"File extension must be {spec.ext} for {spec.name}."
        job.finished_at = _now()
        job.progress = 100
        job.save(update_fields=["status", "error_text", "finished_at", "progress"])
        return

    total = _count_effective_lines(file_path)

    out = io.StringIO()
    try:
        channel_layer = get_channel_layer()

        # Finalize "used inputs" manifest for this job.
        try:
            used = _discover_used_inputs(file_path, file_path.parent)
            RunJob.objects.filter(id=job_id).update(input_manifest=json.dumps(used))
        except Exception:
            pass

        with transaction.atomic():
            job.status = "running"
            job.started_at = _now()
            job.progress = 0
            job.output_text = ""
            job.error_text = ""
            job.save(
                update_fields=["status", "started_at", "progress", "output_text", "error_text"]
            )

        interp = spec.interpreter_factory()

        # We re-implement "run_file" loop to get per-line progress,
        # without changing DSL grammar.
        base_dir = str(file_path.parent)
        processed = 0
        last_pct = -1
        last_push = 0.0
        with redirect_stdout(out):
            # Some interpreters track base dir internally; set when present.
            if hasattr(interp, "_base_dir"):
                setattr(interp, "_base_dir", base_dir)
            for lineno, raw in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
                # Cancellation check
                if RunJob.objects.filter(id=job_id, cancel_requested=True).exists():
                    RunJob.objects.filter(id=job_id).update(
                        status="cancelled",
                        finished_at=_now(),
                        progress=max(0, min(100, int(round(processed / total * 100)))),
                        output_text=out.getvalue()[-100_000:],
                        error_text="Cancelled by user.",
                    )
                    return

                line = raw.rstrip("\n")
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                processed += 1
                if hasattr(interp, "run_line"):
                    try:
                        interp.run_line(line)
                    except Exception as e:
                        raise RuntimeError(f"{file_path.name}:{lineno}: {e}") from e
                else:
                    raise RuntimeError("Interpreter has no run_line()")

                # Update progress frequently, but throttle DB writes.
                pct = int(min(100, round(processed / total * 100)))
                now = time.monotonic()
                should_push = (pct != last_pct) and (now - last_push >= 0.15 or processed == total)
                if should_push:
                    last_pct = pct
                    last_push = now
                    RunJob.objects.filter(id=job_id).update(
                        progress=pct,
                        output_text=out.getvalue()[-100_000:],  # keep last 100k chars
                    )
                    if channel_layer is not None:
                        async_to_sync(channel_layer.group_send)(
                            f"job_{job_id}",
                            {
                                "type": "job.update",
                                "payload": {
                                    "type": "update",
                                    "id": job_id,
                                    "status": "running",
                                    "progress": pct,
                                    "output_text": out.getvalue()[-100_000:],
                                    "error_text": "",
                                },
                            },
                        )

        RunJob.objects.filter(id=job_id).update(
            status="succeeded",
            finished_at=_now(),
            progress=100,
            output_text=out.getvalue()[-100_000:],
        )
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"job_{job_id}",
                {
                    "type": "job.update",
                    "payload": {
                        "type": "final",
                        "id": job_id,
                        "status": "succeeded",
                        "progress": 100,
                        "output_text": out.getvalue()[-100_000:],
                        "error_text": "",
                    },
                },
            )
    except Exception as e:
        RunJob.objects.filter(id=job_id).update(
            status="failed",
            finished_at=_now(),
            progress=100,
            output_text=out.getvalue()[-100_000:],
            error_text=str(e),
        )
        try:
            channel_layer = get_channel_layer()
            if channel_layer is not None:
                async_to_sync(channel_layer.group_send)(
                    f"job_{job_id}",
                    {
                        "type": "job.update",
                        "payload": {
                            "type": "final",
                            "id": job_id,
                            "status": "failed",
                            "progress": 100,
                            "output_text": out.getvalue()[-100_000:],
                            "error_text": str(e),
                        },
                    },
                )
        except Exception:
            pass

