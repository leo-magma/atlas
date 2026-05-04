"""Athena DSL command implementations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from atlas.std import io as atlas_io

from .errors import AthenaRuntimeError, UnknownCommandError, UnknownVariableError
from .features import apply_feature_methods
from .io.load import load_object
from .models.regression import train_table
from .models.wrapper import TrainedModel

Env = dict[str, Any]
CommandFn = Callable[..., Any]


def _lookup(env: Env, name: str) -> Any:
    if name not in env:
        raise UnknownVariableError(f"Unknown variable: {name}")
    return env[name]


def cmd_load(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AthenaRuntimeError("load requires a file path")
    return atlas_io.load_csv(arg, base_dir)


def cmd_load_curve(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AthenaRuntimeError("load_curve requires a file path")
    return atlas_io.load_csv(arg, base_dir)


def cmd_load_bond_impl(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AthenaRuntimeError("load_bond requires a file path")
    return atlas_io.load_csv(arg, base_dir)


def cmd_load_option(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AthenaRuntimeError("load_option requires a file path")
    return atlas_io.load_csv(arg, base_dir)


def cmd_features(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AthenaRuntimeError("features requires a frame variable")
    df = _lookup(env, arg)
    if not isinstance(df, pd.DataFrame):
        raise AthenaRuntimeError("features expects a pandas DataFrame")
    methods = kwargs.get("methods")
    if not methods:
        raise AthenaRuntimeError("features requires methods=...")
    window = int(kwargs.get("window", "20"))
    pca_n = int(kwargs.get("pca_components", "3"))
    return apply_feature_methods(df, methods, window=window, pca_components=pca_n)


def cmd_train(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AthenaRuntimeError("train requires a feature frame variable")
    feat = _lookup(env, arg)
    if not isinstance(feat, pd.DataFrame):
        raise AthenaRuntimeError("train expects a DataFrame from features")
    target = kwargs.get("target")
    algo = kwargs.get("algo", "linear")
    if not target:
        raise AthenaRuntimeError("train requires target=COLUMN")
    window = int(kwargs.get("window", "20"))
    return train_table(feat, target=target, algo=algo, window=window)


def _parse_horizon(spec: str) -> int:
    spec = spec.strip().strip('"').strip("'")
    digits = "".join(ch for ch in spec if ch.isdigit())
    if not digits:
        raise AthenaRuntimeError(f"Could not parse horizon from {spec!r}")
    return int(digits)


def cmd_predict(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AthenaRuntimeError("predict requires a trained model variable")
    model = _lookup(env, arg)
    if not isinstance(model, TrainedModel):
        raise AthenaRuntimeError("predict first argument must be a trained model")
    horizon = kwargs.get("horizon")
    if horizon is not None:
        steps = _parse_horizon(horizon)
        return model.forecast_naive(steps)
    if not args:
        raise AthenaRuntimeError("predict requires a feature frame or horizon=...")
    feat = _lookup(env, args[0])
    if not isinstance(feat, pd.DataFrame):
        raise AthenaRuntimeError("predict expects a DataFrame")
    pred = model.predict_frame(feat)
    return pd.Series(pred, index=feat.index, name="pred")


def _metric_rmse(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - p) ** 2)))


def _metric_mae(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.abs(y - p)))


def _metric_mape(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.abs((y - p) / (np.abs(y) + 1e-12))) * 100.0)


def _metric_r2(y: np.ndarray, p: np.ndarray) -> float:
    ss_res = float(np.sum((y - p) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2)) + 1e-12
    return 1.0 - ss_res / ss_tot


def _metric_sharpe(y: np.ndarray, p: np.ndarray) -> float:
    # Proxy: Sharpe-like score on prediction residuals (not excess returns)
    r = y - p
    m = float(np.mean(r))
    s = float(np.std(r)) + 1e-12
    return m / s


def _metric_drawdown(y: np.ndarray, p: np.ndarray) -> float:
    err = np.abs(y - p)
    curve = np.cumsum(-err)
    peak = np.maximum.accumulate(curve)
    dd = curve - peak
    return float(np.min(dd))


def _metric_accuracy(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(y.astype(int) == p.astype(int)))


def cmd_evaluate(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AthenaRuntimeError("evaluate requires a model variable")
    model = _lookup(env, arg)
    if not isinstance(model, TrainedModel):
        raise AthenaRuntimeError("evaluate expects a trained model")
    if not args:
        raise AthenaRuntimeError("evaluate requires a feature frame variable")
    feat = _lookup(env, args[0])
    if not isinstance(feat, pd.DataFrame):
        raise AthenaRuntimeError("evaluate expects a DataFrame")
    target = kwargs.get("target")
    if not target or target not in feat.columns:
        raise AthenaRuntimeError("evaluate requires target=COLUMN present in frame")
    metrics_spec = kwargs.get("metrics", "rmse")
    metrics = [m.strip() for m in metrics_spec.replace("[", "").replace("]", "").split(",")]

    y = feat[target].replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0).to_numpy()
    p = model.predict_frame(feat)
    scores: dict[str, float] = {}
    for m in metrics:
        key = m.lower()
        if key == "rmse":
            scores["rmse"] = _metric_rmse(y, p)
        elif key == "mae":
            scores["mae"] = _metric_mae(y, p)
        elif key == "mape":
            scores["mape"] = _metric_mape(y, p)
        elif key == "r2":
            scores["r2"] = _metric_r2(y, p)
        elif key == "sharpe":
            scores["sharpe"] = _metric_sharpe(y, p)
        elif key == "drawdown":
            scores["drawdown"] = _metric_drawdown(y, p)
        elif key == "accuracy":
            scores["accuracy"] = _metric_accuracy(y, p)
        else:
            raise AthenaRuntimeError(f"Unknown metric: {m!r}")
    return scores


def cmd_load_model(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    path = arg or kwargs.get("from")
    if not path:
        raise AthenaRuntimeError("load_model requires a path or from=PATH")
    return load_object(path, base_dir)


def cmd_print(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AthenaRuntimeError("print requires a variable name")
    val = _lookup(env, arg)
    print(val)
    return None


_COMMANDS: dict[str, CommandFn] = {
    "load": cmd_load,
    "load_curve": cmd_load_curve,
    "load_bond": cmd_load_bond_impl,
    "load_option": cmd_load_option,
    "features": cmd_features,
    "train": cmd_train,
    "predict": cmd_predict,
    "evaluate": cmd_evaluate,
    "load_model": cmd_load_model,
    "print": cmd_print,
}


def run_command(
    func: str,
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    fn = _COMMANDS.get(func)
    if fn is None:
        raise UnknownCommandError(f"Unknown command: {func!r}")
    return fn(arg, args, kwargs, env, base_dir)
