"""Yield curve with string tenor labels (1Y, 6M, …) and linear interpolation in years."""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..errors import NeptuneRuntimeError


def tenor_to_years(label: str) -> float:
    s = str(label).strip().upper()
    m = re.fullmatch(r"(\d+)([YM])", s)
    if not m:
        raise NeptuneRuntimeError(f"Unsupported tenor label: {label!r}")
    n, u = int(m.group(1)), m.group(2)
    return n / 12.0 if u == "M" else float(n)


@dataclass
class YieldCurve:
    """Sorted tenors (years) and zero-like rates (annual, continuous discount exp(-r t))."""

    tenors_years: np.ndarray
    rates: np.ndarray

    @classmethod
    def from_csv(cls, path: str) -> YieldCurve:
        df = pd.read_csv(path)
        xs = np.array([tenor_to_years(t) for t in df["tenor"]], dtype=float)
        ys = np.array(df["rate"].astype(float), dtype=float)
        order = np.argsort(xs)
        return cls(xs[order], ys[order])

    def interpolate(self, t: float) -> float:
        if t <= float(self.tenors_years[0]):
            return float(self.rates[0])
        if t >= float(self.tenors_years[-1]):
            return float(self.rates[-1])
        return float(np.interp(t, self.tenors_years, self.rates))
