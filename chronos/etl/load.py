"""Load tabular CSV into a DataFrame with optional datetime index."""

from __future__ import annotations

import os

import pandas as pd

from ..errors import ChronosRuntimeError
from ..runtime import resolve_path


def load_csv(path: str, base_dir: str | None, date_column: str | None = None) -> pd.DataFrame:
    resolved = resolve_path(path.strip('"').strip("'"), base_dir)
    if not os.path.isfile(resolved):
        raise ChronosRuntimeError(f"File not found: {resolved}")
    df = pd.read_csv(resolved)
    col = date_column or ("date" if "date" in df.columns else None)
    if col and col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        df = df.set_index(col).sort_index()
    return df
