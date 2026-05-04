"""Standard I/O helpers (CSV load, column selection)."""

from __future__ import annotations

import os

import pandas as pd

from ..errors import AtlasRuntimeError
from ..runtime import resolve_path


def load_csv(path: str, base_dir: str | None) -> pd.DataFrame:
    """Load a CSV into a DataFrame; relative paths resolve from ``base_dir``."""
    resolved = resolve_path(path.strip('"').strip("'"), base_dir)
    if not os.path.isfile(resolved):
        raise AtlasRuntimeError(f"CSV not found: {resolved}")
    return pd.read_csv(resolved)


def select_column(df: pd.DataFrame, column: str | None, args: list[str]) -> pd.DataFrame:
    """Return a single-column DataFrame."""
    col = column
    if col is None and args:
        col = args[0]
    if not col:
        raise AtlasRuntimeError("select requires column=NAME or a positional column name")
    if col not in df.columns:
        raise AtlasRuntimeError(f"Unknown column {col!r}; available: {list(df.columns)}")
    return df[[col]].copy()
