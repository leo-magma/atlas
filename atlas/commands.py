"""DSL command implementations (dispatch to stdlib and builtins)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from .errors import AtlasRuntimeError, UnknownFunctionError, UnknownVariableError
from .runtime import as_dataframe
from .std import io, stats

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
