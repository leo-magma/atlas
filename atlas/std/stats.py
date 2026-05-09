"""Standard statistical primitives for risk scripts."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import binomtest, jarque_bera, norm

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
    out = float(level)
    if not 0.0 < out < 1.0:
        raise AtlasRuntimeError("level must be strictly between 0 and 1")
    return out


def _non_empty_numeric(df: pd.DataFrame, label: str) -> pd.DataFrame:
    out = df.apply(pd.to_numeric, errors="coerce")
    if out.dropna(how="all").empty:
        raise AtlasRuntimeError(f"{label} requires at least one numeric observation")
    return out


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
        bad = s.dropna() <= 0
        if bool(bad.any()):
            raise AtlasRuntimeError("log returns require strictly positive price levels")
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
    if w < 2:
        raise AtlasRuntimeError("vol window must be at least 2")
    s = _series_from_frame(df)
    return s.rolling(w).std().to_frame(name=f"vol_{w}")


def historical_var(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    """Per-column historical VaR at ``level`` (default 0.95)."""
    level = _confidence_level(args, kwargs)
    df = _non_empty_numeric(df, "historical VaR")
    q = 1.0 - level
    s = df.quantile(q)
    s.name = f"var_{level:g}"
    return s


def parametric_var(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    """Gaussian VaR at the same tail mass as historical (left tail ``1 - level``)."""
    level = _confidence_level(args, kwargs)
    df = _non_empty_numeric(df, "parametric VaR")
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
    return pd.Series(out, name=f"var_{level:g}")


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
    df = _non_empty_numeric(df, "historical ES")
    alpha = 1.0 - level
    q = df.quantile(alpha)
    out: dict[Any, float] = {}
    for col in df.columns:
        s = df[col]
        thr = q[col]
        tail = s[s <= thr]
        out[col] = float(tail.mean()) if len(tail) else float("nan")
    return pd.Series(out, name=f"es_{level:g}")


def parametric_es(
    df: pd.DataFrame,
    args: list[str],
    kwargs: dict[str, str],
) -> pd.Series:
    """Gaussian expected shortfall (left tail mean) at confidence ``level``."""
    level = _confidence_level(args, kwargs)
    df = _non_empty_numeric(df, "parametric ES")
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
    return pd.Series(out, name=f"es_{level:g}")


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


def summary(df: pd.DataFrame) -> pd.Series:
    """Basic distribution diagnostics for a single return series."""
    s = _series_from_frame(df).astype(float).dropna()
    if len(s) == 0:
        return pd.Series(
            {
                "n": 0.0,
                "mean": float("nan"),
                "std": float("nan"),
                "skew": float("nan"),
                "kurt": float("nan"),
                "min": float("nan"),
                "p05": float("nan"),
                "p50": float("nan"),
                "p95": float("nan"),
                "max": float("nan"),
            }
        )
    qs = s.quantile([0.05, 0.5, 0.95])
    return pd.Series(
        {
            "n": float(len(s)),
            "mean": float(s.mean()),
            "std": float(s.std(ddof=1)),
            "skew": float(s.skew()),
            "kurt": float(s.kurt()),
            "min": float(s.min()),
            "p05": float(qs.loc[0.05]),
            "p50": float(qs.loc[0.5]),
            "p95": float(qs.loc[0.95]),
            "max": float(s.max()),
        }
    )


def jb_test(df: pd.DataFrame) -> pd.Series:
    """Jarque–Bera normality test for a single series."""
    s = _series_from_frame(df).astype(float).dropna()
    if len(s) < 3:
        return pd.Series({"jb": float("nan"), "pvalue": float("nan")})
    stat, p = jarque_bera(s.to_numpy())
    return pd.Series({"jb": float(stat), "pvalue": float(p)})


def drawdown(df: pd.DataFrame) -> pd.DataFrame:
    """Return a drawdown series computed from a return stream."""
    s = _series_from_frame(df).astype(float).fillna(0.0)
    wealth = (1.0 + s).cumprod()
    peak = wealth.cummax()
    dd = wealth / peak - 1.0
    return dd.to_frame(name="drawdown")


def max_drawdown(df: pd.DataFrame) -> pd.Series:
    d = drawdown(df).iloc[:, 0]
    out = float(d.min()) if len(d) else float("nan")
    return pd.Series({"max_drawdown": out})


def lincomb(df: pd.DataFrame, weights: list[float]) -> pd.DataFrame:
    """Linear combination of columns in a wide return matrix."""
    if df.shape[1] < 1:
        raise AtlasRuntimeError("lincomb requires at least one column")
    if len(weights) != df.shape[1]:
        raise AtlasRuntimeError(f"weights length {len(weights)} must match columns {df.shape[1]}")
    w = np.asarray(weights, dtype=float)
    vals = df.fillna(0.0).to_numpy() @ w
    return pd.DataFrame(vals, index=df.index, columns=["portfolio"])


def var_backtest(returns: pd.DataFrame, var_value: float | pd.Series, level: float) -> pd.Series:
    """Kupiec-style exceedance diagnostics for a VaR threshold.

    Convention: VaR is a left-tail quantile (negative for losses). An exceedance is r <= VaR.
    """
    if not 0.0 < float(level) < 1.0:
        raise AtlasRuntimeError("level must be strictly between 0 and 1")
    s = _series_from_frame(returns).astype(float).dropna()
    if len(s) == 0:
        return pd.Series({"n": 0.0, "exceed": 0.0, "rate": float("nan"), "expected": float("nan")})
    if isinstance(var_value, pd.Series) and len(var_value) > 1:
        v = var_value.astype(float).dropna()
        joined = pd.concat([s.rename("returns"), v.rename("var")], axis=1, join="inner").dropna()
        if joined.empty:
            raise AtlasRuntimeError("var_backtest returns and VaR series have no overlapping index")
        hit = (joined["returns"] <= joined["var"]).astype(int)
    else:
        v = float(var_value.iloc[0]) if isinstance(var_value, pd.Series) else float(var_value)
        hit = (s <= v).astype(int)
    n = int(len(hit))
    x = int(hit.sum())
    rate = x / n if n else float("nan")
    expected = 1.0 - float(level)
    return pd.Series(
        {
            "n": float(n),
            "exceed": float(x),
            "rate": float(rate),
            "expected": float(expected),
        }
    )


def rolling_historical_var_series(s: pd.Series, window: int, level: float) -> pd.Series:
    """Rolling left-tail VaR (quantile) using the previous ``window`` observations."""
    if window < 2:
        raise AtlasRuntimeError("rolling window must be at least 2")
    if not 0.0 < float(level) < 1.0:
        raise AtlasRuntimeError("level must be strictly between 0 and 1")
    q = 1.0 - float(level)
    return s.rolling(int(window)).quantile(q)


def rolling_parametric_var_series(s: pd.Series, window: int, level: float) -> pd.Series:
    """Gaussian VaR series using rolling mean / sample std (previous ``window`` rows)."""
    if window < 2:
        raise AtlasRuntimeError("rolling window must be at least 2")
    if not 0.0 < float(level) < 1.0:
        raise AtlasRuntimeError("level must be strictly between 0 and 1")
    tau = 1.0 - float(level)
    mu = s.rolling(int(window)).mean()
    sigma = s.rolling(int(window)).std(ddof=1)
    out = mu + sigma * float(norm.ppf(tau))
    return out


def var_validation_metrics(
    returns: pd.DataFrame,
    var_value: float | pd.Series,
    level: float,
    metrics: list[str],
) -> pd.Series:
    """Backtesting metrics for VaR: hit ratio, Kupiec p-value (exact binomial), avg exceedance depth."""
    if not metrics:
        raise AtlasRuntimeError("validation requires at least one metric")
    if not 0.0 < float(level) < 1.0:
        raise AtlasRuntimeError("level must be strictly between 0 and 1")
    unknown = [m for m in metrics if m not in ("hit_ratio", "kupiec_p", "avg_exceed")]
    if unknown:
        raise AtlasRuntimeError(f"Unknown validation metric(s): {unknown}")

    s = _series_from_frame(returns).astype(float).dropna()
    if len(s) == 0:
        out: dict[str, float] = {}
        for m in metrics:
            out[m] = float("nan")
        return pd.Series(out)

    if isinstance(var_value, pd.Series) and len(var_value) > 1:
        v = var_value.astype(float)
        joined = pd.concat([s.rename("returns"), v.rename("var")], axis=1, join="inner").dropna()
        if joined.empty:
            raise AtlasRuntimeError("validation: returns and VaR series have no overlapping index")
        hit = (joined["returns"] <= joined["var"]).astype(int)
        r = joined["returns"]
        vj = joined["var"]
    else:
        v_scalar = float(var_value.iloc[0]) if isinstance(var_value, pd.Series) else float(var_value)
        hit = (s <= v_scalar).astype(int)
        r = s
        vj = pd.Series(v_scalar, index=s.index)

    n = int(len(hit))
    x = int(hit.sum())
    p0 = 1.0 - float(level)
    out_map: dict[str, float] = {}
    for m in metrics:
        if m == "hit_ratio":
            out_map[m] = float(x / n) if n else float("nan")
        elif m == "kupiec_p":
            if n == 0:
                out_map[m] = float("nan")
            else:
                out_map[m] = float(binomtest(x, n, p=p0, alternative="two-sided").pvalue)
        else:  # avg_exceed
            viol = hit.astype(bool)
            if viol.any():
                out_map[m] = float((r[viol] - vj[viol]).mean())
            else:
                out_map[m] = float("nan")
    return pd.Series(out_map)
