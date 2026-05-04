"""Clustering trainers."""

from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans


def fit_kmeans(X: pd.DataFrame, n_clusters: int = 3, random_state: int = 0) -> KMeans:
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init="auto")
    km.fit(X.replace([pd.NA], 0.0).fillna(0.0).to_numpy())
    return km
