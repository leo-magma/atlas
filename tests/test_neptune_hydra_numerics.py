from datetime import date

import pytest

from hydra.data.analytics import implied_vol
from hydra.data.option import Option
from hydra.errors import HydraRuntimeError
from neptune.data.analytics import ytm_from_price
from neptune.data.bond import Bond
from neptune.errors import NeptuneRuntimeError


def test_hydra_implied_vol_rejects_no_arbitrage_violation():
    opt = Option(
        underlying="X",
        kind="call",
        spot=100.0,
        strike=100.0,
        maturity=date(2026, 1, 1),
        rate=0.0,
        div_yield=0.0,
    )
    with pytest.raises(HydraRuntimeError, match="no-arbitrage"):
        implied_vol(opt, 1.0, market_price=150.0)


def test_neptune_ytm_solver_error_is_domain_specific():
    bond = Bond(
        isin="X",
        ticker="X",
        name="Bad Price Bond",
        coupon=0.02,
        issue_date=date(2024, 1, 1),
        maturity=date(2030, 1, 1),
        frequency=2,
        face_value=100.0,
        currency="JPY",
        price=10_000_000.0,
    )
    with pytest.raises(NeptuneRuntimeError, match="Could not solve yield"):
        ytm_from_price(bond, valuation=date(2024, 1, 2))
