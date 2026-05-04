"""Lightweight volatility / GARCH-style proxy without extra heavy deps (v0)."""

from __future__ import annotations

import numpy as np
import pandas as pd


class EWMAVolModel:
    """EWMA volatility on returns; ``predict`` returns conditional vol for rows."""

    def __init__(self, span: int = 20) -> None:
        self.span = span
        self._sigma_end: float = 0.0

    def fit(self, y: pd.Series) -> None:
        r = y.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        vol = r.ewm(span=self.span, adjust=False).std(bias=False)
        self._sigma_end = float(vol.iloc[-1]) if len(vol) else 0.0

    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:  # noqa: ARG002
        n = len(X)
        return np.full(n, self._sigma_end)


def fit_garch_proxy(y: pd.Series, span: int = 20) -> EWMAVolModel:
    m = EWMAVolModel(span=span)
    m.fit(y)
    return m
