"""Chronos command implementations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from .errors import ChronosRuntimeError, UnknownCommandError, UnknownVariableError
from .etl import clean, load, normalize
from .etl import join as join_mod
from .ts import diff as diff_mod
from .ts import resample as resample_mod
from .ts import rolling as rolling_mod
from .ts import shift as shift_mod
from .ts import stats as stats_mod

Env = dict[str, Any]
CommandFn = Callable[..., Any]


def _lookup(env: Env, name: str) -> Any:
    if name not in env:
        raise UnknownVariableError(f"Unknown variable: {name}")
    return env[name]


def _truthy(s: str | None) -> bool:
    if s is None:
        return False
    return s.lower() in ("1", "true", "yes", "y")


def cmd_load(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise ChronosRuntimeError("load requires a path")
    date_col = kwargs.get("date_column")
    return load.load_csv(arg, base_dir, date_col)


def cmd_clean(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = _lookup(env, arg or "")
    if not isinstance(df, pd.DataFrame):
        raise ChronosRuntimeError("clean expects a DataFrame")
    return clean.clean_frame(
        df,
        dropna=_truthy(kwargs.get("dropna")),
        ffill=_truthy(kwargs.get("ffill")),
        bfill=_truthy(kwargs.get("bfill")),
    )


def cmd_join(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg or not args:
        raise ChronosRuntimeError("join needs left and right frame names")
    left = _lookup(env, arg)
    right = _lookup(env, args[0])
    if not isinstance(left, pd.DataFrame) or not isinstance(right, pd.DataFrame):
        raise ChronosRuntimeError("join expects two DataFrames")
    return join_mod.join_inner(left, right)


def cmd_resample(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = _lookup(env, arg or "")
    if not isinstance(df, pd.DataFrame):
        raise ChronosRuntimeError("resample expects a DataFrame")
    freq = kwargs.get("freq") or (args[0] if args else None)
    if not freq:
        raise ChronosRuntimeError("resample requires freq=...")
    method = kwargs.get("method", "last")
    return resample_mod.resample_frame(df, freq, method)


def cmd_shift(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = _lookup(env, arg or "")
    if not isinstance(df, pd.DataFrame):
        raise ChronosRuntimeError("shift expects a DataFrame")
    p = int(kwargs.get("periods", args[0] if args else "1"))
    return shift_mod.shift_frame(df, p)


def cmd_validate(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    """Validate a time-series frame and return a small report dict."""
    df = _lookup(env, arg or "")
    if not isinstance(df, pd.DataFrame):
        raise ChronosRuntimeError("validate expects a DataFrame")

    report: dict[str, Any] = {}
    report["rows"] = int(df.shape[0])
    report["cols"] = int(df.shape[1])
    report["columns"] = list(map(str, df.columns))

    idx = df.index
    report["index_type"] = type(idx).__name__
    report["index_is_monotonic_increasing"] = bool(getattr(idx, "is_monotonic_increasing", False))

    try:
        report["index_has_duplicates"] = bool(idx.has_duplicates)
    except Exception:
        report["index_has_duplicates"] = False

    # Missing values summary (top-level only)
    na_total = int(df.isna().sum().sum())
    report["na_total"] = na_total
    if na_total:
        na_by_col = df.isna().sum().sort_values(ascending=False)
        report["na_by_column_top5"] = {str(k): int(v) for k, v in na_by_col.head(5).items()}
    else:
        report["na_by_column_top5"] = {}

    # DatetimeIndex specific checks
    if isinstance(idx, pd.DatetimeIndex):
        report["index_min"] = idx.min().isoformat() if len(idx) else None
        report["index_max"] = idx.max().isoformat() if len(idx) else None
        report["index_is_timezone_aware"] = idx.tz is not None
    else:
        report["index_min"] = None
        report["index_max"] = None
        report["index_is_timezone_aware"] = False

    strict = _truthy(kwargs.get("strict"))
    if strict:
        if report["index_has_duplicates"]:
            raise ChronosRuntimeError("validate(strict=true): index has duplicates")
        if isinstance(idx, pd.DatetimeIndex) and idx.isna().any():
            raise ChronosRuntimeError("validate(strict=true): datetime index contains NaT")

    return report


def cmd_diff(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = _lookup(env, arg or "")
    if not isinstance(df, pd.DataFrame):
        raise ChronosRuntimeError("diff expects a DataFrame")
    periods = int(kwargs.get("periods", "1"))
    col = kwargs.get("column")
    return diff_mod.diff_frame(df, periods=periods, column=col)


def cmd_normalize(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = _lookup(env, arg or "")
    if not isinstance(df, pd.DataFrame):
        raise ChronosRuntimeError("normalize expects a DataFrame")
    method = kwargs.get("method", args[0] if args else "zscore")
    col = kwargs.get("column")
    return normalize.normalize_frame(df, method=method, column=col)


def cmd_rolling_mean(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = _lookup(env, arg or "")
    if not isinstance(df, pd.DataFrame):
        raise ChronosRuntimeError("rolling_mean expects a DataFrame")
    w = int(kwargs.get("window", args[0] if args else "5"))
    col = kwargs.get("column")
    return rolling_mod.rolling_mean(df, w, column=col)


def cmd_describe(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    df = _lookup(env, arg or "")
    if not isinstance(df, pd.DataFrame):
        raise ChronosRuntimeError("describe expects a DataFrame")
    return stats_mod.describe_frame(df)


def cmd_print(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise ChronosRuntimeError("print requires a variable name")
    print(_lookup(env, arg))


def get_command_table() -> dict[str, CommandFn]:
    return {
        "load": cmd_load,
        "clean": cmd_clean,
        "join": cmd_join,
        "resample": cmd_resample,
        "shift": cmd_shift,
        "validate": cmd_validate,
        "diff": cmd_diff,
        "normalize": cmd_normalize,
        "rolling_mean": cmd_rolling_mean,
        "describe": cmd_describe,
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
        raise UnknownCommandError(f"Unknown function: {func}")
    return table[func](arg, args, kwargs, env, base_dir)
