"""DSL command implementations (dispatch to stdlib and builtins)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from .errors import AtlasRuntimeError, UnknownFunctionError, UnknownVariableError
from .runtime import as_dataframe
from .std import io, portfolio, stats

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
        raise AtlasRuntimeError("load requires a file path")
    return io.load_csv(arg, base_dir)


def cmd_select(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return io.select_column(df, kwargs.get("column"), args)


def cmd_bind(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    """Horizontally concatenate single-column frames (inner join on index)."""
    if not arg:
        raise AtlasRuntimeError("bind requires at least two frame names (e.g. bind ra rb)")
    names = [arg] + list(args)
    if len(names) < 2:
        raise AtlasRuntimeError("bind needs at least two inputs")
    parts: list[pd.DataFrame] = []
    for n in names:
        df = as_dataframe(_lookup(env, n))
        if df.shape[1] != 1:
            raise AtlasRuntimeError(f"{n!r} must be a single-column frame; use select first")
        col = df.columns[0]
        parts.append(df.rename(columns={col: n}))
    return pd.concat(parts, axis=1, join="inner")


def cmd_returns(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.compute_returns(df, args, kwargs)


def cmd_vol(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.rolling_vol(df, args, kwargs)


def cmd_var(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.compute_var(df, args, kwargs)


def cmd_es(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.compute_es(df, args, kwargs)


def cmd_corr(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.correlation_matrix(df)


def cmd_cov(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.covariance_matrix(df)


def cmd_beta(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    mkt = kwargs.get("mkt")
    if not arg or not mkt:
        raise AtlasRuntimeError("beta requires asset frame and mkt=benchmark")
    asset_df = as_dataframe(_lookup(env, arg))
    mkt_df = as_dataframe(_lookup(env, mkt))
    return stats.ols_beta(asset_df, mkt_df)


def cmd_sharpe(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.sharpe_ratio(df, args, kwargs)


def cmd_summary(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.summary(df)


def cmd_jb(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.jb_test(df)


def cmd_drawdown(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.drawdown(df)


def cmd_maxdd(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = as_dataframe(_lookup(env, arg or ""))
    return stats.max_drawdown(df)


def _parse_weights(spec: str) -> list[float]:
    raw = spec.strip().strip('"').strip("'")
    raw = raw.replace("[", "").replace("]", "")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [float(p) for p in parts]


def cmd_lincomb(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AtlasRuntimeError("lincomb requires a wide DataFrame variable")
    df = as_dataframe(_lookup(env, arg))
    wspec = kwargs.get("weights")
    if not wspec:
        raise AtlasRuntimeError("lincomb requires weights=0.6,0.4,...")
    w = _parse_weights(wspec)
    return stats.lincomb(df, w)


def cmd_var_backtest(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AtlasRuntimeError("var_backtest requires a returns frame variable")
    df = as_dataframe(_lookup(env, arg))
    vname = kwargs.get("var")
    if not vname:
        raise AtlasRuntimeError("var_backtest requires var=VAR_SERIES")
    v = _lookup(env, vname)
    if not isinstance(v, pd.Series) or len(v) < 1:
        raise AtlasRuntimeError("var_backtest var= must be a non-empty Series (result of var)")
    level = float(kwargs.get("level", "0.95"))
    return stats.var_backtest(df, v, level=level)


def cmd_min_var(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AtlasRuntimeError("min_var requires a wide returns matrix variable")
    df = as_dataframe(_lookup(env, arg))
    return portfolio.min_variance_weights(df, kwargs)


def cmd_tangency(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AtlasRuntimeError("tangency requires a wide returns matrix variable")
    df = as_dataframe(_lookup(env, arg))
    return portfolio.tangency_weights(df, kwargs)


def cmd_efficient_frontier(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AtlasRuntimeError("efficient_frontier requires a wide returns matrix variable")
    df = as_dataframe(_lookup(env, arg))
    return portfolio.efficient_frontier(df, args, kwargs)


def cmd_print(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise AtlasRuntimeError("print requires a variable name")
    value = _lookup(env, arg)
    # Pretty-print single-scalar Series as "label: value" to avoid
    # outputs like "close    -0.0044" for VaR/ES.
    if isinstance(value, pd.Series) and len(value) == 1:
        label = str(value.name) if value.name is not None else arg
        label = label.split("_", 1)[0]  # var_0.95 -> var, es_0.95 -> es
        try:
            v = float(value.iloc[0])
            print(f"{label}: {v:.6g}")
        except Exception:
            print(f"{label}: {value.iloc[0]}")
        return
    print(value)


def get_command_table() -> dict[str, CommandFn]:
    return {
        "load": cmd_load,
        "select": cmd_select,
        "bind": cmd_bind,
        "returns": cmd_returns,
        "vol": cmd_vol,
        "var": cmd_var,
        "es": cmd_es,
        "corr": cmd_corr,
        "cov": cmd_cov,
        "beta": cmd_beta,
        "sharpe": cmd_sharpe,
        "summary": cmd_summary,
        "jb": cmd_jb,
        "drawdown": cmd_drawdown,
        "maxdd": cmd_maxdd,
        "lincomb": cmd_lincomb,
        "var_backtest": cmd_var_backtest,
        "min_var": cmd_min_var,
        "tangency": cmd_tangency,
        "efficient_frontier": cmd_efficient_frontier,
        "print": cmd_print,
    }


def run_command(
    func: str,
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
) -> Any:
    table = get_command_table()
    if func not in table:
        raise UnknownFunctionError(f"Unknown function: {func}")
    return table[func](arg, args, kwargs, env, base_dir)
