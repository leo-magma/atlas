"""Standard statistical primitives for risk scripts."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm

from ..errors import AtlasRuntimeError


def _series_from_frame(df: pd.DataFrame) -> pd.Series:
    if df.shape[1] == 1:
        return df.iloc[:, 0]
    raise AtlasRuntimeError(
        "Expected a single-column DataFrame; use select ... column=... first"
    )


def _confidence_level(args: list[str], kwargs: dict[str, str]) -> float:
    level = kwargs.get("level")
    if level is None and args:
        level = args[0]
    if level is None:
        level = "0.95"
    return float(level)


def _var_method(kwargs: dict[str, str]) -> tuple[str, dict[str, str]]:
    kw = dict(kwargs)
    method = (kw.pop("method", None) or "historical").lower()
    return method, kw


def compute_returns(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.DataFrame:
    """Simple or log returns; kwargs ``method`` or first positional overrides default."""
    method = kwargs.get("method")
    if method is None and args:
        method = args[0]
    if method is None:
        method = "simple"
    s = _series_from_frame(df)
    if method in ("log", "ln"):
        out = np.log(s / s.shift(1))
    elif method in ("simple", "pct", "arithmetic"):
        out = s.pct_change()
    else:
        raise AtlasRuntimeError(f"Unknown returns method: {method!r}")
    return out.dropna().to_frame(name=s.name or "return")


def rolling_vol(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.DataFrame:
    """Rolling standard deviation of returns (default window 21)."""
    window = kwargs.get("window")
    if window is None and args:
        window = args[0]
    if window is None:
        window = "21"
    w = int(window)
    s = _series_from_frame(df)
    return s.rolling(w).std().to_frame(name=f"vol_{w}")


def historical_var(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    """Per-column historical VaR at ``level`` (default 0.95)."""
    alpha = _confidence_level(args, kwargs)
    q = 1.0 - alpha
    return df.quantile(q)


def parametric_var(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    """Gaussian VaR at the same tail mass as historical (left tail ``1 - level``)."""
    level = _confidence_level(args, kwargs)
    tau = 1.0 - level
    out: dict[Any, float] = {}
    for col in df.columns:
        s = df[col].dropna()
        if len(s) < 2:
            out[col] = float("nan")
            continue
        mu, sigma = float(s.mean()), float(s.std(ddof=1))
        if sigma == 0.0 or not np.isfinite(sigma):
            out[col] = float("nan")
        else:
            out[col] = mu + sigma * float(norm.ppf(tau))
    return pd.Series(out)


def compute_var(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    method, kw = _var_method(kwargs)
    if method in ("historical", "hist", "empirical"):
        return historical_var(df, args, kw)
    if method in ("parametric", "normal", "gaussian"):
        return parametric_var(df, args, kw)
    raise AtlasRuntimeError(f"Unknown var method: {method!r}")


def historical_es(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    """Mean of returns at or below the historical VaR threshold (per column)."""
    level = _confidence_level(args, kwargs)
    alpha = 1.0 - level
    q = df.quantile(alpha)
    out: dict[Any, float] = {}
    for col in df.columns:
        s = df[col]
        thr = q[col]
        tail = s[s <= thr]
        out[col] = float(tail.mean()) if len(tail) else float("nan")
    return pd.Series(out)


def parametric_es(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    """Gaussian expected shortfall (left tail mean) at confidence ``level``."""
    level = _confidence_level(args, kwargs)
    tau = 1.0 - level
    if tau <= 0.0 or tau >= 1.0:
        raise AtlasRuntimeError("level must be strictly between 0 and 1 for parametric ES")
    z = float(norm.ppf(tau))
    out: dict[Any, float] = {}
    for col in df.columns:
        s = df[col].dropna()
        if len(s) < 2:
            out[col] = float("nan")
            continue
        mu, sigma = float(s.mean()), float(s.std(ddof=1))
        if sigma == 0.0 or not np.isfinite(sigma):
            out[col] = float("nan")
        else:
            # E[X | X at or below Gaussian tau-quantile] = mu - sigma * phi(z) / tau
            out[col] = mu - sigma * float(norm.pdf(z) / tau)
    return pd.Series(out)


def compute_es(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    method, kw = _var_method(kwargs)
    if method in ("historical", "hist", "empirical"):
        return historical_es(df, args, kw)
    if method in ("parametric", "normal", "gaussian"):
        return parametric_es(df, args, kw)
    raise AtlasRuntimeError(f"Unknown es method: {method!r}")


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation matrix (multi-column returns)."""
    if df.shape[1] < 2:
        raise AtlasRuntimeError("corr requires at least two columns (wide return matrix)")
    return df.corr(method="pearson", min_periods=2)


def covariance_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Sample covariance matrix (multi-column returns)."""
    if df.shape[1] < 2:
        raise AtlasRuntimeError("cov requires at least two columns (wide return matrix)")
    return df.cov(min_periods=2)


def ols_beta(
    asset: pd.DataFrame,
    mkt: pd.DataFrame,
) -> pd.Series:
    """CAPM-style OLS beta: Cov(r_asset, r_mkt) / Var(r_mkt) on overlapping rows."""
    y = asset.iloc[:, 0].astype(float)
    x = mkt.iloc[:, 0].astype(float)
    joined = pd.concat([y, x], axis=1, keys=["asset", "mkt"]).dropna()
    if len(joined) < 3:
        raise AtlasRuntimeError("Not enough overlapping observations for beta")
    c = joined.cov(ddof=1)
    var_m = float(c.loc["mkt", "mkt"])
    if var_m == 0.0:
        raise AtlasRuntimeError("Market variance is zero; cannot compute beta")
    beta = float(c.loc["asset", "mkt"] / var_m)
    return pd.Series({"beta": beta})


def sharpe_ratio(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    """Annualized Sharpe: (mean / std) * sqrt(periods); default ``periods=252``."""
    periods = kwargs.get("periods")
    if periods is None and args:
        periods = args[0]
    if periods is None:
        periods = "252"
    ann = float(periods)
    s = _series_from_frame(df).astype(float)
    if len(s) < 2:
        return pd.Series({"sharpe": float("nan")})
    ex = float(s.mean())
    sd = float(s.std(ddof=1))
    if sd == 0.0 or not np.isfinite(sd):
        return pd.Series({"sharpe": float("nan")})
    return pd.Series({"sharpe": (ex / sd) * (ann**0.5)})
