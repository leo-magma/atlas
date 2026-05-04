"""Time-series feature methods (Chronos-style numerics on DataFrames)."""

from __future__ import annotations

import pandas as pd

from athena.errors import AthenaRuntimeError

from .pca import append_pca
from .risk import apply_risk_methods


def _split_methods(spec: str) -> list[str]:
    return [p.strip() for p in spec.replace("[", "").replace("]", "").split(",") if p.strip()]


def apply_feature_methods(
    df: pd.DataFrame,
    methods_spec: str,
    *,
    window: int = 20,
    pca_components: int = 3,
) -> pd.DataFrame:
    """Apply comma-separated method names; returns a new frame with ``f_*`` columns."""
    methods = _split_methods(methods_spec)
    if not methods:
        raise AthenaRuntimeError("features requires methods=... with at least one method")

    risk_subset = [m for m in methods if m in ("duration", "convexity", "spread")]
    ts_methods = [m for m in methods if m not in risk_subset]

    out = df.copy()
    if risk_subset:
        out = apply_risk_methods(out, risk_subset)

    for raw in ts_methods:
        m = raw.strip().lower()
        if m == "diff":
            for c in out.select_dtypes(include=["number"]).columns:
                out[f"f_diff_{c}"] = out[c].diff()
        elif m == "pct_change":
            for c in out.select_dtypes(include=["number"]).columns:
                out[f"f_pct_{c}"] = out[c].pct_change()
        elif m == "rolling_mean":
            for c in out.select_dtypes(include=["number"]).columns:
                out[f"f_rm_{c}"] = out[c].rolling(window=window, min_periods=1).mean()
        elif m == "rolling_std":
            for c in out.select_dtypes(include=["number"]).columns:
                out[f"f_rstd_{c}"] = out[c].rolling(window=window, min_periods=1).std()
        elif m == "zscore":
            for c in out.select_dtypes(include=["number"]).columns:
                s = out[c]
                out[f"f_z_{c}"] = (s - s.rolling(window=window, min_periods=1).mean()) / (
                    s.rolling(window=window, min_periods=1).std() + 1e-12
                )
        elif m == "normalize":
            for c in out.select_dtypes(include=["number"]).columns:
                s = out[c]
                lo = s.min()
                hi = s.max()
                out[f"f_norm_{c}"] = (s - lo) / (hi - lo + 1e-12)
        elif m == "volatility":
            for c in out.select_dtypes(include=["number"]).columns:
                r = out[c].pct_change()
                out[f"f_vol_{c}"] = r.rolling(window=window, min_periods=1).std()
        elif m == "correlation":
            num = out.select_dtypes(include=["number"])
            if num.shape[1] < 2:
                raise AthenaRuntimeError("correlation needs at least two numeric columns")
            a, b = num.columns[0], num.columns[1]
            out["f_corr_rolling"] = num[a].rolling(window=window, min_periods=2).corr(num[b])
        elif m == "pca":
            out = append_pca(out, n_components=pca_components)
        else:
            raise AthenaRuntimeError(f"Unknown feature method: {raw!r}")

    return out
