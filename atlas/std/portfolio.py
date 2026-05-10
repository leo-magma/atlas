"""Long-only mean–variance portfolio optimization and efficient frontier."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ..errors import AtlasRuntimeError


def _parse_bool(s: str | None, default: bool) -> bool:
    if s is None:
        return default
    return str(s).strip().lower() in ("1", "true", "yes", "y", "on")


def _periods(kwargs: dict[str, str]) -> int:
    p = kwargs.get("periods", "252")
    return max(1, int(p))


def _returns_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, pd.Index]:
    if df.shape[1] < 2:
        raise AtlasRuntimeError("portfolio optimization requires a wide return matrix (≥2 columns); use bind")
    r = df.astype(float).dropna(how="any")
    if len(r) < 3:
        raise AtlasRuntimeError("need at least 3 complete return observations for stable covariance")
    mu = r.mean().to_numpy(dtype=float)
    cov = r.cov().to_numpy(dtype=float)
    if np.linalg.matrix_rank(cov) < 2:
        raise AtlasRuntimeError("return covariance matrix is rank-deficient; check for collinear series")
    return mu, cov, r.columns


def _solve_min_variance_pure(
    cov: np.ndarray,
    x0: np.ndarray,
    bounds: tuple[tuple[float | None, float | None], ...],
) -> np.ndarray:
    cons = ({"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)},)
    res = minimize(lambda w: float(w @ cov @ w), x0, method="SLSQP", bounds=bounds, constraints=cons)
    if not res.success:
        raise AtlasRuntimeError(f"min variance optimization failed: {res.message}")
    return res.x.astype(float)


def min_variance_weights(df: pd.DataFrame, kwargs: dict[str, str]) -> pd.Series:
    """Global minimum-variance portfolio (optionally long-only)."""
    _mu, cov, cols = _returns_matrix(df)
    long_only = _parse_bool(kwargs.get("long_only"), True)
    n = len(_mu)
    x0 = np.ones(n, dtype=float) / n

    bounds = tuple((0.0, 1.0) for _ in range(n)) if long_only else tuple((None, None) for _ in range(n))
    w = _solve_min_variance_pure(cov, x0, bounds)
    return pd.Series(w, index=cols, name="weights")


def tangency_weights(df: pd.DataFrame, kwargs: dict[str, str]) -> pd.Series:
    """Maximize Sharpe ratio (per-period mean/vol, scaled by sqrt(periods) in objective)."""
    mu, cov, cols = _returns_matrix(df)
    long_only = _parse_bool(kwargs.get("long_only"), True)
    periods = _periods(kwargs)
    rf = float(kwargs.get("rf", "0"))
    n = len(mu)
    x0 = np.ones(n, dtype=float) / n

    def neg_sharpe(w: np.ndarray) -> float:
        m = float(w @ mu)
        v = float(w @ cov @ w)
        if v < 1e-20:
            return 1e12
        ann_m = m * periods
        ann_v = (v**0.5) * (periods**0.5)
        if ann_v < 1e-12:
            return 1e12
        return -(ann_m - rf) / ann_v

    cons = ({"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)},)
    bounds = tuple((0.0, 1.0) for _ in range(n)) if long_only else tuple((None, None) for _ in range(n))
    res = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=cons)
    if not res.success:
        raise AtlasRuntimeError(f"tangency (max Sharpe) optimization failed: {res.message}")
    w = res.x.astype(float)
    return pd.Series(w, index=cols, name="weights")


def efficient_frontier(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.DataFrame:
    """Sample the long-only frontier by sweeping target mean return and minimizing variance."""
    mu, cov, cols = _returns_matrix(df)
    long_only = _parse_bool(kwargs.get("long_only"), True)
    periods = _periods(kwargs)
    n_pts = int(kwargs.get("points", args[0] if args else "25"))
    n_pts = max(3, min(200, n_pts))

    n = len(mu)
    x0 = np.ones(n, dtype=float) / n
    bounds = tuple((0.0, 1.0) for _ in range(n)) if long_only else tuple((None, None) for _ in range(n))

    def min_var_for_target(target: float) -> np.ndarray | None:
        cons = (
            {"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)},
            {"type": "eq", "fun": lambda w: float(w @ mu - target)},
        )
        res = minimize(lambda w: float(w @ cov @ w), x0, method="SLSQP", bounds=bounds, constraints=cons)
        if not res.success:
            return None
        return res.x.astype(float)

    w_m = _solve_min_variance_pure(cov, x0, bounds)
    r_low = float(w_m @ mu)
    r_high = float(np.max(mu))
    if r_high <= r_low + 1e-12:
        raise AtlasRuntimeError("frontier range degenerate; check return dispersion across assets")
    targets = np.linspace(r_low, r_high, n_pts)
    rows: list[dict[str, float]] = []
    for t in targets:
        w = min_var_for_target(float(t))
        if w is None:
            continue
        m = float(w @ mu)
        v = float(w @ cov @ w)
        vol = (v**0.5) * (periods**0.5)
        mean_ann = m * periods
        sharpe = (mean_ann - float(kwargs.get("rf", "0"))) / vol if vol > 1e-12 else float("nan")
        row: dict[str, float] = {"mean": mean_ann, "vol": vol, "sharpe": sharpe}
        for i, c in enumerate(cols):
            row[str(c)] = float(w[i])
        rows.append(row)
    if len(rows) < 2:
        raise AtlasRuntimeError("could not trace efficient frontier; try fewer constraints or more data")
    return pd.DataFrame(rows)

