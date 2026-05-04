import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from atlas.commands import run_command
from atlas.std.stats import compute_var, ols_beta


def test_parametric_var_matches_normal_quantile():
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"x": rng.normal(0.0, 1.0, size=80_000)})
    out = compute_var(df, ["0.95"], {"method": "parametric"})
    assert out["x"] == pytest.approx(float(norm.ppf(0.05)), abs=0.02)


def test_ols_beta_recovers_slope():
    rng = np.random.default_rng(7)
    x = rng.normal(0.0, 1.0, size=500)
    y = 1.35 * x + rng.normal(0.0, 0.05, size=500)
    asset = pd.DataFrame({"y": y})
    mkt = pd.DataFrame({"x": x})
    b = ols_beta(asset, mkt)
    assert b["beta"] == pytest.approx(1.35, rel=0.05)


def test_bind_cov_corr_roundtrip():
    env: dict = {}
    ra = pd.DataFrame({"a": [0.01, 0.02, -0.01, 0.0]})
    rb = pd.DataFrame({"b": [0.02, 0.03, -0.02, 0.01]})
    env["ra"] = ra
    env["rb"] = rb
    wide = run_command("bind", "ra", ["rb"], {}, env, None)
    env["rets"] = wide
    cov_m = run_command("cov", "rets", [], {}, env, None)
    corr_m = run_command("corr", "rets", [], {}, env, None)
    assert cov_m.shape == (2, 2)
    assert corr_m.shape == (2, 2)
    assert float(corr_m.iloc[0, 1]) == pytest.approx(float(corr_m.iloc[1, 0]))


def test_sharpe_command():
    env = {"r": pd.DataFrame({"x": [0.01] * 30 + [-0.02] * 30})}
    out = run_command("sharpe", "r", [], {"periods": "252"}, env, None)
    assert np.isfinite(float(out.loc["sharpe"]))
