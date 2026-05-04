"""Vanilla bond record."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


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
        return Bond(
            isin=str(row["isin"]),
            ticker=str(row["ticker"]),
            name=str(row["name"]),
            coupon=float(row["coupon"]),
            issue_date=pd.to_datetime(row["issue_date"]).date(),
            maturity=pd.to_datetime(row["maturity"]).date(),
            frequency=int(row["frequency"]),
            face_value=float(row["face_value"]),
            currency=str(row["currency"]),
            price=float(row["price"]) if "price" in row and pd.notna(row.get("price")) else None,
            yield_=float(row["yield_"])
            if "yield_" in row and pd.notna(row.get("yield_"))
            else None,
        )
