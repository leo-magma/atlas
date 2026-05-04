import pandas as pd
import pytest

from atlas.std.stats import historical_var


def test_historical_var_quantile_matches_pandas():
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5]})
    out = historical_var(df, ["0.95"], {})
    assert out["x"] == pytest.approx(1.2)
    assert out["x"] == pytest.approx(df["x"].quantile(0.05))
