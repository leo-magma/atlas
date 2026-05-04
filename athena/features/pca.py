"""PCA-based feature columns."""

from __future__ import annotations

import pandas as pd


def append_pca(df: pd.DataFrame, n_components: int = 3, prefix: str = "f_pca") -> pd.DataFrame:
    """Append ``prefix_*`` columns from PCA on numeric columns of ``df``."""
    try:
        from sklearn.decomposition import PCA  # type: ignore
    except ImportError as e:
        raise ImportError("PCA feature requires scikit-learn: pip install scikit-learn") from e

    num = df.select_dtypes(include=["number"]).copy()
    if num.shape[1] == 0:
        raise ValueError("PCA requires at least one numeric column")
    n = min(n_components, num.shape[1])
    pca = PCA(n_components=n, random_state=0)
    comps = pca.fit_transform(num.fillna(0.0))
    out = df.copy()
    for j in range(comps.shape[1]):
        out[f"{prefix}_{j}"] = comps[:, j]
    return out
