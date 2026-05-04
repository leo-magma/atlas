"""Summary statistics."""

from __future__ import annotations

import pandas as pd


def describe_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.describe(include="all")
