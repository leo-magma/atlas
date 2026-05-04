"""Missing-value handling."""

from __future__ import annotations

import pandas as pd


def clean_frame(
    df: pd.DataFrame,
    *,
    dropna: bool = False,
    ffill: bool = False,
    bfill: bool = False,
) -> pd.DataFrame:
    out = df.copy()
    if ffill:
        out = out.ffill()
    if bfill:
        out = out.bfill()
    if dropna:
        out = out.dropna(how="any")
    return out
