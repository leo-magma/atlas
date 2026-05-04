"""Serialize trained objects with joblib."""

from __future__ import annotations

import os

from atlas.runtime import resolve_path


def save_object(path: str, obj: object, base_dir: str | None) -> str:
    try:
        import joblib  # type: ignore
    except ImportError as e:
        raise ImportError("Model IO requires joblib: pip install joblib") from e

    resolved = resolve_path(path.strip('"').strip("'"), base_dir)
    parent = os.path.dirname(resolved)
    if parent:
        os.makedirs(parent, exist_ok=True)
    joblib.dump(obj, resolved)
    return resolved
