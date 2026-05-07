"""Hydra command implementations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pandas as pd

from .data import analytics
from .data.option import Option
from .data.vol_surface import VolSurface
from .errors import HydraRuntimeError, UnknownCommandError, UnknownVariableError
from .runtime import resolve_path

Env = dict[str, Any]
CommandFn = Callable[..., Any]


def _lookup(env: Env, name: str) -> Any:
    if name not in env:
        raise UnknownVariableError(f"Unknown variable: {name}")
    return env[name]


def _as_of(kwargs: dict[str, str]) -> date:
    if "as_of" in kwargs:
        return pd.to_datetime(kwargs["as_of"]).date()
    return date.today()


def _year_fraction(opt: Option, as_of: date) -> float:
    t = (pd.Timestamp(opt.maturity) - pd.Timestamp(as_of)).days / 365.0
    if t <= 0:
        raise HydraRuntimeError("Option maturity must be after as_of")
    return float(t)


def _sigma(opt: Option, T: float, kwargs: dict[str, str], env: Env) -> float:
    if opt.vol is not None:
        return float(opt.vol)
    surf_name = kwargs.get("vol_surface")
    if surf_name:
        surf = _lookup(env, surf_name)
        if not isinstance(surf, VolSurface):
            raise HydraRuntimeError("vol_surface must be a VolSurface")
        return surf.interpolate(T, opt.strike)
    raise HydraRuntimeError("Need option.vol or vol_surface=...")


def cmd_load_option(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise HydraRuntimeError("load_option requires a path")
    path = resolve_path(arg.strip('"').strip("'"), base_dir)
    df = pd.read_csv(path)
    if df.empty:
        raise HydraRuntimeError("Option CSV is empty")
    return Option.from_csv_row(df.iloc[0])


def cmd_load_vol_surface(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise HydraRuntimeError("load_vol_surface requires a path")
    path = resolve_path(arg.strip('"').strip("'"), base_dir)
    as_of = pd.Timestamp(_as_of(kwargs))
    return VolSurface.from_csv(path, as_of)


def cmd_price(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    opt = _lookup(env, arg or "")
    if not isinstance(opt, Option):
        raise HydraRuntimeError("price needs an option")
    if kwargs.get("model", "bs").lower() != "bs":
        raise HydraRuntimeError("Only model=bs is supported")
    as_of = _as_of(kwargs)
    T = _year_fraction(opt, as_of)
    sig = _sigma(opt, T, kwargs, env)
    px = analytics.bs_price(opt, T, sig)
    return pd.Series({"price": px})


def cmd_greeks(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    opt = _lookup(env, arg or "")
    if not isinstance(opt, Option):
        raise HydraRuntimeError("greeks needs an option")
    if kwargs.get("model", "bs").lower() != "bs":
        raise HydraRuntimeError("Only model=bs is supported")
    as_of = _as_of(kwargs)
    T = _year_fraction(opt, as_of)
    sig = _sigma(opt, T, kwargs, env)
    g = analytics.bs_greeks(opt, T, sig)
    return pd.Series(g)


def cmd_implied_vol(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    opt = _lookup(env, arg or "")
    if not isinstance(opt, Option):
        raise HydraRuntimeError("implied_vol needs an option")
    px = kwargs.get("price")
    if px is None:
        raise HydraRuntimeError("implied_vol needs price=...")
    market = float(px)
    as_of = _as_of(kwargs)
    T = _year_fraction(opt, as_of)
    iv = analytics.implied_vol(opt, T, market)
    return pd.Series({"implied_vol": iv})


def cmd_print(
    arg: str | None,
    args: list[str],
    kwargs: dict[str, str],
    env: Env,
    base_dir: str | None,
):
    if not arg:
        raise HydraRuntimeError("print needs a variable name")
    print(_lookup(env, arg))


def get_command_table() -> dict[str, CommandFn]:
    return {
        "load_option": cmd_load_option,
        "load_vol_surface": cmd_load_vol_surface,
        "price": cmd_price,
        "greeks": cmd_greeks,
        "implied_vol": cmd_implied_vol,
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
