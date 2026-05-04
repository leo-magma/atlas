"""Bond / risk columns used as features (pass-through or explicit errors)."""

from __future__ import annotations

import pandas as pd

from athena.errors import AthenaRuntimeError


def apply_risk_methods(df: pd.DataFrame, methods: list[str]) -> pd.DataFrame:
    """Ensure requested risk columns exist; v0 does not compute duration from cashflows."""
    out = df.copy()
    for m in methods:
        if m in ("duration", "convexity", "spread"):
            if m not in out.columns:
                raise AthenaRuntimeError(
                    f"Feature method {m!r} requires column {m!r} in the frame "
                    "(v0: pre-compute in Neptune or join before features)."
                )
    return out
