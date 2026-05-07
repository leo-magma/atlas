"""Neptune command implementations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pandas as pd

from .data import analytics
from .data.bond import Bond
from .data.yield_curve import YieldCurve
from .errors import NeptuneRuntimeError, UnknownCommandError, UnknownVariableError
from .runtime import resolve_path

Env = dict[str, Any]
CommandFn = Callable[..., Any]


def _lookup(env: Env, name: str) -> Any:
    if name not in env:
        raise UnknownVariableError(f"Unknown variable: {name}")
    return env[name]


def _valuation(kwargs: dict[str, str]) -> date:
    if "as_of" in kwargs:
        return pd.to_datetime(kwargs["as_of"]).date()
    return date.today()


def cmd_load_bond(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise NeptuneRuntimeError("load_bond requires a path")
    path = resolve_path(arg.strip('"').strip("'"), base_dir)
    df = pd.read_csv(path)
    if df.empty:
        raise NeptuneRuntimeError("Bond CSV is empty")
    return Bond.from_csv_row(df.iloc[0])


def cmd_load_curve(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise NeptuneRuntimeError("load_curve requires a path")
    path = resolve_path(arg.strip('"').strip("'"), base_dir)
    return YieldCurve.from_csv(path)


def cmd_price(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    bond = _lookup(env, arg or "")
    curve = _lookup(env, kwargs.get("curve", ""))
    if not isinstance(bond, Bond) or not isinstance(curve, YieldCurve):
        raise NeptuneRuntimeError("price needs bond and curve=...")
    val = _valuation(kwargs)
    px = analytics.price_from_curve(bond, curve, val)
    return pd.Series({"price": px})


def cmd_yield(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    bond = _lookup(env, arg or "")
    if not isinstance(bond, Bond):
        raise NeptuneRuntimeError("yield needs a bond")
    val = _valuation(kwargs)
    y = analytics.ytm_from_price(bond, val)
    return pd.Series({"yield": y})


def cmd_duration(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    bond = _lookup(env, arg or "")
    if not isinstance(bond, Bond):
        raise NeptuneRuntimeError("duration needs a bond")
    val = _valuation(kwargs)
    ytm = analytics.ytm_from_price(bond, val)
    dmod = analytics.modified_duration(bond, val, ytm)
    dmac = analytics.macaulay_duration(bond, val, ytm)
    return pd.Series({"modified_duration": dmod, "macaulay_duration": dmac})


def cmd_convexity(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    bond = _lookup(env, arg or "")
    if not isinstance(bond, Bond):
        raise NeptuneRuntimeError("convexity needs a bond")
    val = _valuation(kwargs)
    ytm = analytics.ytm_from_price(bond, val)
    cx = analytics.convexity_bond(bond, val, ytm)
    return pd.Series({"convexity": cx})


def cmd_dv01(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    bond = _lookup(env, arg or "")
    if not isinstance(bond, Bond):
        raise NeptuneRuntimeError("dv01 needs a bond")
    val = _valuation(kwargs)
    ytm = analytics.ytm_from_price(bond, val)
    dv = analytics.dv01_bond(bond, val, ytm)
    return pd.Series({"dv01": dv})


def cmd_spread(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    bond = _lookup(env, arg or "")
    curve = _lookup(env, kwargs.get("benchmark", kwargs.get("curve", "")))
    if not isinstance(bond, Bond) or not isinstance(curve, YieldCurve):
        raise NeptuneRuntimeError("spread needs bond and benchmark=curve")
    val = _valuation(kwargs)
    z = analytics.z_spread(bond, curve, val)
    return pd.Series({"z_spread": z})


def cmd_print(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise NeptuneRuntimeError("print needs a variable name")
    print(_lookup(env, arg))


def get_command_table() -> dict[str, CommandFn]:
    return {
        "load_bond": cmd_load_bond,
        "load_curve": cmd_load_curve,
        "price": cmd_price,
        "yield": cmd_yield,
        "duration": cmd_duration,
        "convexity": cmd_convexity,
        "dv01": cmd_dv01,
        "spread": cmd_spread,
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
