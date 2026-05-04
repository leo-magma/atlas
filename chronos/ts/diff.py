"""Differences."""

from __future__ import annotations

import pandas as pd

from ..errors import ChronosRuntimeError


def diff_frame(df: pd.DataFrame, periods: int = 1, column: str | None = None) -> pd.DataFrame:
    if column:
        if column not in df.columns:
            raise ChronosRuntimeError(f"Unknown column: {column!r}")
        out = df.copy()
        out[column] = out[column].diff(periods=periods)
        return out
    return df.diff(periods=periods)
