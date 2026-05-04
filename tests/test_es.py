import pandas as pd
import pytest

from atlas.std.stats import historical_es


def test_historical_es_left_tail_mean_monotone_sample():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
    es = historical_es(df, ["0.95"], {})
    thr = float(df["x"].quantile(0.05))
    manual = float(df.loc[df["x"] <= thr, "x"].mean())
    assert es["x"] == pytest.approx(manual)
