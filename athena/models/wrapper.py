"""Unified handle returned by ``train`` for ``predict`` / ``evaluate`` / IO."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from athena.errors import AthenaRuntimeError


@dataclass
class TrainedModel:
    """Trained estimator plus column metadata."""

    algo: str
    estimator: Any
    feature_columns: list[str]
    target_column: str
    horizon_steps: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def predict_frame(self, df: pd.DataFrame) -> np.ndarray:
        missing = [c for c in self.feature_columns if c not in df.columns]
        if missing:
            raise AthenaRuntimeError(f"predict missing feature columns: {missing}")
        Xdf = df[self.feature_columns].replace([np.inf, -np.inf], np.nan)
        if Xdf.isna().any().any():
            raise AthenaRuntimeError("predict requires complete feature rows; clean or drop missing values first")
        if not hasattr(self.estimator, "predict"):
            raise TypeError("Estimator has no predict")
        kind = self.extra.get("kind")
        if kind == "garch_proxy":
            return np.asarray(self.estimator.predict(Xdf))
        return np.asarray(self.estimator.predict(Xdf.to_numpy()))

    def forecast_naive(self, steps: int) -> pd.Series:
        """Used when ``predict`` is called with ``horizon=`` (v0 naive level hold)."""
        last = float(self.extra.get("last_level", 0.0))
        return pd.Series([last] * steps, name=self.target_column)
