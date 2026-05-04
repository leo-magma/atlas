"""Column-wise normalization."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..errors import ChronosRuntimeError


def _zscore(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    std = s.std(ddof=1)
    if std == 0 or not np.isfinite(std):
        return pd.Series(np.nan, index=s.index)
    return (s - s.mean()) / std


def _minmax(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    lo, hi = s.min(), s.max()
    if hi == lo:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


def normalize_frame(
    df: pd.DataFrame,
    method: str = "zscore",
    column: str | None = None,
) -> pd.DataFrame:
    m = method.lower()
    if m in ("zscore", "z"):
        fn = _zscore
    elif m in ("minmax", "01"):
        fn = _minmax
    else:
        raise ChronosRuntimeError(f"Unknown normalize method: {method!r}")
    if column:
        if column not in df.columns:
            raise ChronosRuntimeError(f"Unknown column: {column!r}")
        out = df.copy()
        out[column] = fn(out[column])
        return out
    return df.apply(lambda s: fn(s) if s.dtype.kind in "fiu" else s)
