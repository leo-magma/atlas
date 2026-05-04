"""Runtime helpers for the Atlas interpreter."""

from __future__ import annotations

import os
from typing import Any


def resolve_path(path: str, base_dir: str | None) -> str:
    """Resolve a user path; relative paths are anchored to base_dir when given."""
    if not path:
        return path
    if os.path.isabs(path) or base_dir is None:
        return path
    return os.path.normpath(os.path.join(base_dir, path))


def as_dataframe(obj: Any):
    """Return obj if it is a DataFrame; raise otherwise."""
    import pandas as pd

    if isinstance(obj, pd.DataFrame):
        return obj
    raise TypeError(f"Expected pandas.DataFrame, got {type(obj).__name__}")
