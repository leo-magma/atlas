"""Rolling window aggregates."""

from __future__ import annotations

import pandas as pd

from ..errors import ChronosRuntimeError


def rolling_mean(df: pd.DataFrame, window: int, column: str | None = None) -> pd.DataFrame:
    if column:
        if column not in df.columns:
            raise ChronosRuntimeError(f"Unknown column: {column!r}")
        out = df.copy()
        out[f"{column}_rmean_{window}"] = out[column].rolling(window).mean()
        return out
    return df.rolling(window).mean()
