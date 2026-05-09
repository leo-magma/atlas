import pandas as pd
import pytest

from atlas.errors import AtlasRuntimeError
from atlas.std import stats


def test_invalid_var_level_is_rejected():
    df = pd.DataFrame({"r": [0.01, -0.02, 0.03]})
    with pytest.raises(AtlasRuntimeError, match="level"):
        stats.historical_var(df, [], {"level": "1.5"})


def test_log_returns_reject_non_positive_levels():
    df = pd.DataFrame({"close": [100.0, 0.0, 101.0]})
    with pytest.raises(AtlasRuntimeError, match="strictly positive"):
        stats.compute_returns(df, ["log"], {})


def test_var_validation_metrics_scalar_var():
    returns = pd.DataFrame({"r": [-0.03, -0.01, 0.02, -0.04]})
    out = stats.var_validation_metrics(returns, -0.02, 0.95, ["hit_ratio", "kupiec_p"])
    assert out["hit_ratio"] == pytest.approx(0.5)
    assert 0.0 <= out["kupiec_p"] <= 1.0


def test_var_backtest_aligns_indexed_var_series():
    returns = pd.DataFrame({"r": [-0.03, -0.01, -0.04]}, index=pd.date_range("2024-01-01", periods=3))
    var = pd.Series([-0.02, -0.02], index=returns.index[1:])
    out = stats.var_backtest(returns, var, level=0.95)
    assert out["n"] == 2.0
    assert out["exceed"] == 1.0
    assert out["rate"] == pytest.approx(0.5)


def test_lincomb_weight_mismatch_rejected():
    df = pd.DataFrame({"a": [0.01], "b": [0.02]})
    with pytest.raises(AtlasRuntimeError, match="weights length"):
        stats.lincomb(df, [1.0])
