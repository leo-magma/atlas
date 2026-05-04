"""Path helpers (same contract as Atlas: relative paths from script dir)."""

from __future__ import annotations

import os


def resolve_path(path: str, base_dir: str | None) -> str:
    if not path:
        return path
    if os.path.isabs(path) or base_dir is None:
        return path
    return os.path.normpath(os.path.join(base_dir, path))
