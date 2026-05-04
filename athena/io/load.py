"""Load serialized objects."""

from __future__ import annotations

import joblib

from atlas.runtime import resolve_path


def load_object(path: str, base_dir: str | None) -> object:
    resolved = resolve_path(path.strip('"').strip("'"), base_dir)
    return joblib.load(resolved)
