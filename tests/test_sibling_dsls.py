from pathlib import Path

import pytest

from chronos.core import ChronosInterpreter
from hydra.core import HydraInterpreter
from neptune.core import NeptuneInterpreter

ROOT = Path(__file__).resolve().parents[1]


def test_chronos_example_runs():
    ChronosInterpreter().run_file(str(ROOT / "chronos" / "examples" / "example.chr"))


def test_neptune_example_runs():
    NeptuneInterpreter().run_file(str(ROOT / "neptune" / "examples" / "example.nep"))


def test_hydra_example_runs():
    HydraInterpreter().run_file(str(ROOT / "hydra" / "examples" / "example.hyd"))


def test_hydra_implied_vol_roundtrip():
    from datetime import date

    from hydra.data.analytics import bs_price, implied_vol
    from hydra.data.option import Option

    opt = Option(
        underlying="X",
        kind="call",
        spot=100.0,
        strike=100.0,
        maturity=date(2025, 1, 1),
        rate=0.05,
        div_yield=0.0,
        vol=0.25,
        price=None,
    )
    T = 1.0
    sigma = 0.25
    mkt = bs_price(opt, T, sigma)
    iv = implied_vol(opt, T, mkt)
    assert iv == pytest.approx(sigma, rel=1e-4)
