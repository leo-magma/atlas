"""European option record."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class Option:
    underlying: str
    kind: str
    spot: float
    strike: float
    maturity: date
    rate: float
    div_yield: float
    vol: float | None = None
    price: float | None = None

    @staticmethod
    def from_csv_row(row: pd.Series) -> Option:
        return Option(
            underlying=str(row["underlying"]),
            kind=str(row["type"]).lower(),
            spot=float(row["spot"]),
            strike=float(row["strike"]),
            maturity=pd.to_datetime(row["maturity"]).date(),
            rate=float(row["rate"]),
            div_yield=float(row["div_yield"]),
            vol=float(row["vol"]) if pd.notna(row.get("vol")) else None,
            price=float(row["price"]) if "price" in row and pd.notna(row.get("price")) else None,
        )
