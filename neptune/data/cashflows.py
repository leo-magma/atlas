"""Coupon schedule (generic payment frequency)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from .bond import Bond


def coupon_schedule(bond: Bond) -> tuple[list[date], list[float]]:
    """Payment dates from first coupon after issue through maturity (inclusive)."""
    mstep = 12 // max(1, bond.frequency)
    out_dates: list[date] = []
    d = pd.Timestamp(bond.issue_date) + pd.DateOffset(months=mstep)
    end = pd.Timestamp(bond.maturity)
    while d <= end:
        out_dates.append(d.date())
        d = d + pd.DateOffset(months=mstep)
    if not out_dates:
        out_dates = [bond.maturity]
    cpn = bond.coupon / float(bond.frequency) * bond.face_value
    amounts = [cpn + bond.face_value if dt == bond.maturity else cpn for dt in out_dates]
    return out_dates, amounts


def year_fractions(valuation: date, dates: list[date]) -> np.ndarray:
    v = pd.Timestamp(valuation)
    return np.array([(pd.Timestamp(d) - v).days / 365.0 for d in dates], dtype=float)
