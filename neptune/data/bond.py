"""Vanilla bond record."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from ..errors import NeptuneRuntimeError


@dataclass(frozen=True)
class Bond:
    isin: str
    ticker: str
    name: str
    coupon: float
    issue_date: date
    maturity: date
    frequency: int
    face_value: float
    currency: str
    price: float | None = None
    yield_: float | None = None

    @staticmethod
    def from_csv_row(row: pd.Series) -> Bond:
        required = {"isin", "ticker", "name", "coupon", "issue_date", "maturity", "frequency", "face_value", "currency"}
        missing = sorted(required - set(row.index))
        if missing:
            raise NeptuneRuntimeError(f"Bond CSV missing required columns: {missing}")
        issue_date = pd.to_datetime(row["issue_date"]).date()
        maturity = pd.to_datetime(row["maturity"]).date()
        coupon = float(row["coupon"])
        frequency = int(row["frequency"])
        face_value = float(row["face_value"])
        price = float(row["price"]) if "price" in row and pd.notna(row.get("price")) else None
        if maturity <= issue_date:
            raise NeptuneRuntimeError("Bond maturity must be after issue_date")
        if coupon < 0:
            raise NeptuneRuntimeError("Bond coupon must be non-negative")
        if frequency not in (1, 2, 4, 12):
            raise NeptuneRuntimeError("Bond frequency must be one of 1, 2, 4, or 12")
        if face_value <= 0:
            raise NeptuneRuntimeError("Bond face_value must be positive")
        if price is not None and price <= 0:
            raise NeptuneRuntimeError("Bond price must be positive when provided")
        return Bond(
            isin=str(row["isin"]),
            ticker=str(row["ticker"]),
            name=str(row["name"]),
            coupon=coupon,
            issue_date=issue_date,
            maturity=maturity,
            frequency=frequency,
            face_value=face_value,
            currency=str(row["currency"]),
            price=price,
            yield_=float(row["yield_"])
            if "yield_" in row and pd.notna(row.get("yield_"))
            else None,
        )
