"""Anomaly detection."""

from __future__ import annotations

import pandas as pd

from athena.errors import AthenaRuntimeError


def fit_isolation_forest(X: pd.DataFrame, random_state: int = 0):
    try:
        from sklearn.ensemble import IsolationForest  # type: ignore
    except ImportError as e:
        raise AthenaRuntimeError("algo requires scikit-learn: pip install scikit-learn") from e

    clean = X.replace([pd.NA], pd.NA).dropna()
    if clean.empty:
        raise AthenaRuntimeError("isolation_forest requires complete numeric feature rows")
    iso = IsolationForest(random_state=random_state, contamination="auto")
    iso.fit(clean.to_numpy())
    return iso
