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
    """Validate a time-series frame and return a report dict.

    This is intentionally strict about time-series hygiene, but configurable via kwargs:
    - strict=true: fail on duplicates / NaT in DatetimeIndex
    - require_datetime=true: fail if index is not DatetimeIndex
    - require_columns=col1,col2: fail if missing
    - numeric_columns=col1,col2: fail if missing or not numeric
    - freq=1D|B|W|M: check inferred/expected frequency (best-effort)
    - max_gap=3D: fail if max index gap exceeds the threshold (best-effort)
    """
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

    report["index_has_na"] = False
    if isinstance(idx, pd.DatetimeIndex):
        report["index_has_na"] = bool(idx.isna().any())

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
        # Frequency / gap diagnostics (best-effort)
        try:
            report["inferred_freq"] = pd.infer_freq(idx)  # may be None
        except Exception:
            report["inferred_freq"] = None
        if len(idx) >= 2:
            d = idx.to_series().diff().dropna()
            report["min_gap"] = str(d.min())
            report["max_gap"] = str(d.max())
            report["median_gap"] = str(d.median())
        else:
            report["min_gap"] = None
            report["max_gap"] = None
            report["median_gap"] = None
    else:
        report["index_min"] = None
        report["index_max"] = None
        report["index_is_timezone_aware"] = False
        report["inferred_freq"] = None
        report["min_gap"] = None
        report["max_gap"] = None
        report["median_gap"] = None

    strict = _truthy(kwargs.get("strict"))
    require_datetime = _truthy(kwargs.get("require_datetime"))
    if require_datetime and not isinstance(idx, pd.DatetimeIndex):
        raise ChronosRuntimeError("validate(require_datetime=true): index is not a DatetimeIndex")

    # Column requirements
    req_cols = (kwargs.get("require_columns") or "").strip()
    if req_cols:
        needed = [c.strip() for c in req_cols.replace("[", "").replace("]", "").split(",") if c.strip()]
        missing = [c for c in needed if c not in df.columns]
        report["missing_required_columns"] = missing
        if missing:
            raise ChronosRuntimeError(f"validate: missing required columns: {missing}")
    else:
        report["missing_required_columns"] = []

    num_cols = (kwargs.get("numeric_columns") or "").strip()
    if num_cols:
        needed = [c.strip() for c in num_cols.replace("[", "").replace("]", "").split(",") if c.strip()]
        missing = [c for c in needed if c not in df.columns]
        non_numeric: list[str] = []
        for c in needed:
            if c in df.columns:
                if not pd.api.types.is_numeric_dtype(df[c]):
                    non_numeric.append(c)
        report["missing_numeric_columns"] = missing
        report["non_numeric_columns"] = non_numeric
        if missing:
            raise ChronosRuntimeError(f"validate: missing numeric columns: {missing}")
        if non_numeric:
            raise ChronosRuntimeError(f"validate: expected numeric columns but got non-numeric: {non_numeric}")
    else:
        report["missing_numeric_columns"] = []
        report["non_numeric_columns"] = []

    # Expected frequency / max gap checks (best-effort)
    exp_freq = (kwargs.get("freq") or "").strip()
    if exp_freq:
        report["expected_freq"] = exp_freq
        if isinstance(idx, pd.DatetimeIndex):
            inferred = report.get("inferred_freq")
            report["freq_matches"] = bool(inferred == exp_freq)
        else:
            report["freq_matches"] = False
    else:
        report["expected_freq"] = None
        report["freq_matches"] = None

    max_gap_spec = (kwargs.get("max_gap") or "").strip()
    if max_gap_spec and isinstance(idx, pd.DatetimeIndex) and report.get("max_gap") is not None:
        try:
            thr = pd.to_timedelta(max_gap_spec)
            # report["max_gap"] is a string, reparse from index diffs
            d = idx.to_series().diff().dropna()
            report["max_gap_exceeds"] = bool(d.max() > thr)
            if report["max_gap_exceeds"]:
                raise ChronosRuntimeError(f"validate: max_gap exceeds {thr}")
        except ValueError:
            raise ChronosRuntimeError(f"validate: could not parse max_gap={max_gap_spec!r}")
    else:
        report["max_gap_exceeds"] = None

    if strict:
        if report["index_has_duplicates"]:
            raise ChronosRuntimeError("validate(strict=true): index has duplicates")
        if isinstance(idx, pd.DatetimeIndex) and idx.isna().any():
            raise ChronosRuntimeError("validate(strict=true): datetime index contains NaT")
        if report["index_is_monotonic_increasing"] is False:
            raise ChronosRuntimeError("validate(strict=true): index is not monotonic increasing")

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
