"""Anomaly detection."""

from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest


def fit_isolation_forest(X: pd.DataFrame, random_state: int = 0) -> IsolationForest:
    iso = IsolationForest(random_state=random_state, contamination="auto")
    iso.fit(X.replace([pd.NA], 0.0).fillna(0.0).to_numpy())
    return iso
