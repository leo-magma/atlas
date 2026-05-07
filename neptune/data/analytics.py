"""Bond PV, yield, duration, convexity, DV01, and parallel z-spread (continuous compounding)."""

from __future__ import annotations

import math
from datetime import date

import numpy as np
from scipy.optimize import brentq

from ..errors import NeptuneRuntimeError
from .bond import Bond
from .cashflows import coupon_schedule, year_fractions
from .yield_curve import YieldCurve


def _target_dirty_price(bond: Bond) -> float:
    if bond.price is None:
        raise NeptuneRuntimeError("Bond.price is required for this operation")
    price = float(bond.price)
    if price <= 0 or not math.isfinite(price):
        raise NeptuneRuntimeError("Bond.price must be a positive finite number")
    return price


def npv_continuous(cf: list[float], times: np.ndarray, rates: np.ndarray) -> float:
    """Discount with time-varying continuously compounded rates ``rates`` (same length as flows)."""
    total = 0.0
    for c, t, r in zip(cf, times, rates, strict=True):
        total += c * math.exp(-float(r) * float(t))
    return total


def npv_flat_ytm(cf: list[float], times: np.ndarray, y: float) -> float:
    return float(sum(c * math.exp(-y * float(t)) for c, t in zip(cf, times, strict=True)))


def price_from_curve(bond: Bond, curve: YieldCurve, valuation: date) -> float:
    dates, cf = coupon_schedule(bond)
    t = year_fractions(valuation, dates)
    if np.any(t <= 0):
        raise NeptuneRuntimeError("Valuation must be strictly before all cashflow dates")
    rates = np.array([curve.interpolate(float(ti)) for ti in t], dtype=float)
    return npv_continuous(cf, t, rates)


def ytm_from_price(bond: Bond, valuation: date) -> float:
    dates, cf = coupon_schedule(bond)
    t = year_fractions(valuation, dates)
    if np.any(t <= 0):
        raise NeptuneRuntimeError("Valuation must be strictly before all cashflow dates")
    target = _target_dirty_price(bond)

    def f(y: float) -> float:
        return npv_flat_ytm(cf, t, y) - target

    try:
        return float(brentq(f, -1.0, 1.0, maxiter=200))
    except ValueError as exc:
        raise NeptuneRuntimeError(
            "Could not solve yield: price is inconsistent with cashflows or outside the solver bracket"
        ) from exc


def macaulay_duration(bond: Bond, valuation: date, ytm: float) -> float:
    dates, cf = coupon_schedule(bond)
    t = year_fractions(valuation, dates)
    p = npv_flat_ytm(cf, t, ytm)
    if p == 0:
        raise NeptuneRuntimeError("Zero price in duration")
    dmac = sum(float(ti) * c * math.exp(-ytm * float(ti)) for ti, c in zip(t, cf, strict=True)) / p
    return float(dmac)


def modified_duration(bond: Bond, valuation: date, ytm: float) -> float:
    dmac = macaulay_duration(bond, valuation, ytm)
    m = max(1.0, float(bond.frequency))
    return float(dmac / (1.0 + ytm / m))


def convexity_bond(bond: Bond, valuation: date, ytm: float) -> float:
    dates, cf = coupon_schedule(bond)
    t = year_fractions(valuation, dates)
    p = npv_flat_ytm(cf, t, ytm)
    if p == 0:
        raise NeptuneRuntimeError("Zero price in convexity")
    cx = sum(
        float(ti) ** 2 * c * math.exp(-ytm * float(ti)) for ti, c in zip(t, cf, strict=True)
    ) / p
    return float(cx)


def dv01_bond(bond: Bond, valuation: date, ytm: float, bump: float = 1e-4) -> float:
    dates, cf = coupon_schedule(bond)
    t = year_fractions(valuation, dates)
    p0 = npv_flat_ytm(cf, t, ytm)
    p_up = npv_flat_ytm(cf, t, ytm + bump)
    return float(p_up - p0)


def z_spread(bond: Bond, curve: YieldCurve, valuation: date) -> float:
    """Parallel additive spread (continuous) on top of curve zero rates so PV matches bond.price."""
    dates, cf = coupon_schedule(bond)
    t = year_fractions(valuation, dates)
    if np.any(t <= 0):
        raise NeptuneRuntimeError("Valuation must be strictly before all cashflow dates")
    target = _target_dirty_price(bond)
    base = np.array([curve.interpolate(float(ti)) for ti in t], dtype=float)

    def g(z: float) -> float:
        rates = base + z
        return npv_continuous(cf, t, rates) - target

    try:
        return float(brentq(g, -0.20, 0.20, maxiter=200))
    except ValueError as exc:
        raise NeptuneRuntimeError(
            "Could not solve z-spread: price is inconsistent with the curve or outside the solver bracket"
        ) from exc
