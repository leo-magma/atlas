"""Volatility surface with bilinear-friendly grid (piecewise linear in maturity & strike)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.interpolate import LinearNDInterpolator

from ..errors import HydraRuntimeError


@dataclass
class VolSurface:
    maturities: np.ndarray  # year fractions at load time
    strikes: np.ndarray
    vols: np.ndarray

    @classmethod
    def from_csv(cls, path: str, as_of: pd.Timestamp) -> VolSurface:
        df = pd.read_csv(path)
        mats = []
        for m in df["maturity"]:
            mt = pd.to_datetime(m)
            mats.append(max((mt - as_of).days / 365.0, 1e-6))
        strikes = np.array(df["strike"].astype(float), dtype=float)
        vols = np.array(df["vol"].astype(float), dtype=float)
        return cls(np.array(mats, dtype=float), strikes, vols)

    def interpolate(self, maturity_years: float, strike: float) -> float:
        pts = np.column_stack([self.maturities, self.strikes])
        if len(self.vols) >= 3:
            itp = LinearNDInterpolator(pts, self.vols, fill_value=float(np.nan))
            v = float(itp(maturity_years, strike))
            if np.isnan(v):
                raise HydraRuntimeError("Vol interpolation out of grid hull")
            return v
        j = int(np.argmin((self.strikes - strike) ** 2 + (self.maturities - maturity_years) ** 2))
        return float(self.vols[j])
