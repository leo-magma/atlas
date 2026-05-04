"""Lag / lead."""

from __future__ import annotations

import pandas as pd


def shift_frame(df: pd.DataFrame, periods: int) -> pd.DataFrame:
    return df.shift(periods=periods)
