"""Clustering trainers."""

from __future__ import annotations

import pandas as pd

from athena.errors import AthenaRuntimeError


def fit_kmeans(X: pd.DataFrame, n_clusters: int = 3, random_state: int = 0):
    try:
        from sklearn.cluster import KMeans  # type: ignore
    except ImportError as e:
        raise AthenaRuntimeError("algo requires scikit-learn: pip install scikit-learn") from e

    clean = X.replace([pd.NA], pd.NA).dropna()
    if clean.empty:
        raise AthenaRuntimeError("kmeans requires complete numeric feature rows")
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init="auto")
    km.fit(clean.to_numpy())
    return km
