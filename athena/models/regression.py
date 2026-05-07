"""Regression / tree models used by ``train``."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from athena.errors import AthenaRuntimeError

from .anomaly import fit_isolation_forest
from .classification import fit_logistic
from .clustering import fit_kmeans
from .garch import fit_garch_proxy
from .wrapper import TrainedModel


def _require_extra(pkg: str) -> Any:
    try:
        return __import__(pkg)
    except ImportError as e:
        raise AthenaRuntimeError(
            f"Algorithm requires optional dependency {pkg!r}: pip install {pkg}"
        ) from e


def build_regressor(name: str, seed: int = 0) -> Any:
    try:
        from sklearn.ensemble import RandomForestRegressor  # type: ignore
        from sklearn.linear_model import Lasso, LinearRegression, Ridge  # type: ignore
    except ImportError as e:
        raise AthenaRuntimeError("algo requires scikit-learn: pip install scikit-learn") from e

    n = name.lower()
    if n == "linear":
        return LinearRegression()
    if n == "ridge":
        return Ridge()
    if n == "lasso":
        return Lasso(random_state=seed, max_iter=5000)
    if n == "rf":
        return RandomForestRegressor(n_estimators=50, random_state=seed)
    if n == "lightgbm":
        lgb = _require_extra("lightgbm")
        return lgb.LGBMRegressor(random_state=seed, verbosity=-1)
    if n == "xgboost":
        xgb = _require_extra("xgboost")
        return xgb.XGBRegressor(random_state=seed, n_estimators=50, verbosity=0)
    raise AthenaRuntimeError(f"Unknown or unsupported regression algo: {name!r}")


def train_table(
    feat: pd.DataFrame,
    *,
    target: str,
    algo: str,
    window: int = 20,
    target_shift: int = 0,
    seed: int = 0,
) -> TrainedModel:
    """Supervised train on numeric feature columns (all except target by default).

    ``target_shift`` is a simple leakage guard for time-series: when > 0, the target is shifted
    backward by that many rows (predict future target from current features).
    """
    if target not in feat.columns:
        raise AthenaRuntimeError(f"target column {target!r} not in frame")
    num_cols = list(feat.select_dtypes(include=["number"]).columns)
    if target not in num_cols:
        raise AthenaRuntimeError(f"target {target!r} must be numeric")
    feature_columns = [c for c in num_cols if c != target]
    if not feature_columns:
        raise AthenaRuntimeError("No feature columns after excluding target")

    # Keep chronological order for time-series.
    feat = feat.sort_index()

    if target_shift < 0:
        raise AthenaRuntimeError("target_shift must be >= 0")
    X = feat[feature_columns].replace([np.inf, -np.inf], np.nan)
    y = feat[target].replace([np.inf, -np.inf], np.nan)
    if target_shift > 0:
        y = y.shift(-target_shift)
        X = X.iloc[:-target_shift, :]
        y = y.iloc[:-target_shift]
    aligned = pd.concat([X, y.rename(target)], axis=1).dropna()
    if aligned.empty:
        raise AthenaRuntimeError("No complete training rows after target_shift and missing-value removal")
    if len(aligned) < 2:
        raise AthenaRuntimeError("train requires at least 2 complete observations")
    X = aligned[feature_columns]
    y = aligned[target]

    a = algo.lower()
    if a in ("kmeans",):
        km = fit_kmeans(X, n_clusters=3, random_state=seed)
        tm = TrainedModel(algo=a, estimator=km, feature_columns=feature_columns, target_column=target)
        tm.extra["kind"] = "cluster"
        tm.extra["seed"] = seed
        tm.extra["target_shift"] = target_shift
        tm.extra["missing_policy"] = "drop"
        return tm
    if a in ("isolation_forest",):
        iso = fit_isolation_forest(X, random_state=seed)
        tm = TrainedModel(algo=a, estimator=iso, feature_columns=feature_columns, target_column=target)
        tm.extra["kind"] = "anomaly"
        tm.extra["seed"] = seed
        tm.extra["target_shift"] = target_shift
        tm.extra["missing_policy"] = "drop"
        return tm
    if a in ("logistic",):
        clf = fit_logistic(X, y.astype(int), random_state=seed)
        tm = TrainedModel(algo=a, estimator=clf, feature_columns=feature_columns, target_column=target)
        tm.extra["kind"] = "classify"
        tm.extra["seed"] = seed
        tm.extra["target_shift"] = target_shift
        tm.extra["missing_policy"] = "drop"
        return tm
    if a in ("garch",):
        # Vol proxy on target level changes
        r = y.pct_change().dropna()
        if r.empty:
            raise AthenaRuntimeError("garch proxy requires at least one target change")
        vol_model = fit_garch_proxy(r, span=window)
        tm = TrainedModel(
            algo=a,
            estimator=vol_model,
            feature_columns=feature_columns,
            target_column=target,
            extra={
                "last_level": float(y.iloc[-1]),
                "kind": "garch_proxy",
                "seed": seed,
                "target_shift": target_shift,
                "missing_policy": "drop",
                "model_note": "EWMA volatility proxy, not a full maximum-likelihood GARCH model",
            },
        )
        return tm

    est = build_regressor(a, seed=seed)
    est.fit(X.to_numpy(), y.to_numpy())
    tm = TrainedModel(
        algo=a,
        estimator=est,
        feature_columns=feature_columns,
        target_column=target,
        extra={
            "last_level": float(y.iloc[-1]),
            "kind": "sklearn_regress",
            "seed": seed,
            "target_shift": target_shift,
            "missing_policy": "drop",
        },
    )
    return tm
