"""European option record."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from ..errors import HydraRuntimeError


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
        required = {"underlying", "type", "spot", "strike", "maturity", "rate", "div_yield"}
        missing = sorted(required - set(row.index))
        if missing:
            raise HydraRuntimeError(f"Option CSV missing required columns: {missing}")
        kind = str(row["type"]).lower()
        spot = float(row["spot"])
        strike = float(row["strike"])
        vol = float(row["vol"]) if pd.notna(row.get("vol")) else None
        price = float(row["price"]) if "price" in row and pd.notna(row.get("price")) else None
        if kind not in ("call", "put"):
            raise HydraRuntimeError("Option type must be 'call' or 'put'")
        if spot <= 0 or strike <= 0:
            raise HydraRuntimeError("Option spot and strike must be positive")
        if vol is not None and vol <= 0:
            raise HydraRuntimeError("Option vol must be positive when provided")
        if price is not None and price <= 0:
            raise HydraRuntimeError("Option price must be positive when provided")
        return Option(
            underlying=str(row["underlying"]),
            kind=kind,
            spot=spot,
            strike=strike,
            maturity=pd.to_datetime(row["maturity"]).date(),
            rate=float(row["rate"]),
            div_yield=float(row["div_yield"]),
            vol=vol,
            price=price,
        )
