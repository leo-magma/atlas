"""Align / join frames on index."""

from __future__ import annotations

import pandas as pd


def join_inner(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    return left.join(right, how="inner", rsuffix="_r")
