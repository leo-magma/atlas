"""Resample time series."""

from __future__ import annotations

import pandas as pd

from ..errors import ChronosRuntimeError


def resample_frame(df: pd.DataFrame, freq: str, method: str = "last") -> pd.DataFrame:
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ChronosRuntimeError("resample requires a DatetimeIndex (use load with a date column)")
    rule = freq
    m = method.lower()
    if m == "last":
        return df.resample(rule).last().dropna(how="all")
    if m == "first":
        return df.resample(rule).first().dropna(how="all")
    if m == "mean":
        return df.resample(rule).mean().dropna(how="all")
    raise ChronosRuntimeError(f"Unknown resample method: {method!r}")
