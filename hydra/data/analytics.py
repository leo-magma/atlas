"""Black–Scholes price and Greeks (continuous dividend yield)."""

from __future__ import annotations

import math

from scipy.optimize import brentq
from scipy.stats import norm

from ..errors import HydraRuntimeError
from .option import Option


def _d1_d2(S: float, K: float, T: float, r: float, q: float, sigma: float) -> tuple[float, float]:
    if S <= 0 or K <= 0:
        raise HydraRuntimeError("spot and strike must be positive")
    if T <= 0 or sigma <= 0:
        raise HydraRuntimeError("T and sigma must be positive")
    vsqrt = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / vsqrt
    d2 = d1 - vsqrt
    return d1, d2


def bs_price(opt: Option, T: float, sigma: float) -> float:
    S, K, r, q = opt.spot, opt.strike, opt.rate, opt.div_yield
    d1, d2 = _d1_d2(S, K, T, r, q, sigma)
    if opt.kind == "call":
        return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    if opt.kind == "put":
        return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)
    raise HydraRuntimeError(f"Unknown option kind: {opt.kind!r}")


def bs_greeks(opt: Option, T: float, sigma: float) -> dict[str, float]:
    S, K, r, q = opt.spot, opt.strike, opt.rate, opt.div_yield
    d1, d2 = _d1_d2(S, K, T, r, q, sigma)
    pdf1 = norm.pdf(d1)
    disc_q = math.exp(-q * T)
    disc_r = math.exp(-r * T)
    vsqrt = sigma * math.sqrt(T)
    gamma = disc_q * pdf1 / (S * vsqrt)
    vega = S * disc_q * pdf1 * math.sqrt(T) / 100.0
    if opt.kind == "call":
        delta = disc_q * norm.cdf(d1)
        rho = K * T * disc_r * norm.cdf(d2) / 100.0
        theta = (
            -S * pdf1 * disc_q * sigma / (2 * math.sqrt(T))
            - r * K * disc_r * norm.cdf(d2)
            + q * S * disc_q * norm.cdf(d1)
        ) / 365.0
    elif opt.kind == "put":
        delta = disc_q * (norm.cdf(d1) - 1.0)
        rho = -K * T * disc_r * norm.cdf(-d2) / 100.0
        theta = (
            -S * pdf1 * disc_q * sigma / (2 * math.sqrt(T))
            + r * K * disc_r * norm.cdf(-d2)
            - q * S * disc_q * norm.cdf(-d1)
        ) / 365.0
    else:
        raise HydraRuntimeError(f"Unknown option kind: {opt.kind!r}")
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta, "rho": rho}


def implied_vol(opt: Option, T: float, market_price: float) -> float:
    if market_price <= 0:
        raise HydraRuntimeError("market price must be positive")
    if T <= 0:
        raise HydraRuntimeError("T must be positive for implied volatility")
    disc_s = opt.spot * math.exp(-opt.div_yield * T)
    disc_k = opt.strike * math.exp(-opt.rate * T)
    if opt.kind == "call":
        lower, upper = max(disc_s - disc_k, 0.0), disc_s
    elif opt.kind == "put":
        lower, upper = max(disc_k - disc_s, 0.0), disc_k
    else:
        raise HydraRuntimeError(f"Unknown option kind: {opt.kind!r}")
    eps = 1e-10
    if market_price < lower - eps or market_price > upper + eps:
        raise HydraRuntimeError(
            f"market price violates no-arbitrage bounds [{lower:.6g}, {upper:.6g}]"
        )

    def f(sig: float) -> float:
        return bs_price(opt, T, sig) - market_price

    try:
        return float(brentq(f, 1e-6, 5.0, maxiter=200))
    except ValueError as exc:
        raise HydraRuntimeError("Could not solve implied volatility within bracket [1e-6, 5.0]") from exc
