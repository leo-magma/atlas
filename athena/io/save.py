"""Serialize trained objects with joblib."""

from __future__ import annotations

import os

import joblib

from atlas.runtime import resolve_path


def save_object(path: str, obj: object, base_dir: str | None) -> str:
    resolved = resolve_path(path.strip('"').strip("'"), base_dir)
    parent = os.path.dirname(resolved)
    if parent:
        os.makedirs(parent, exist_ok=True)
    joblib.dump(obj, resolved)
    return resolved
