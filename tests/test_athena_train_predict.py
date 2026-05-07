import numpy as np
import pandas as pd
import pytest

pytest.importorskip("sklearn")

from athena.commands import cmd_evaluate
from athena.errors import AthenaRuntimeError
from athena.models.regression import train_table


def test_train_table_records_seed_and_drops_missing_rows():
    feat = pd.DataFrame(
        {
            "x": [1.0, 2.0, np.nan, 4.0, 5.0],
            "close": [2.0, 4.0, 6.0, 8.0, 10.0],
        }
    )
    model = train_table(feat, target="close", algo="rf", seed=123)
    assert model.extra["seed"] == 123
    assert model.extra["missing_policy"] == "drop"
    pred = model.predict_frame(pd.DataFrame({"x": [6.0]}))
    assert len(pred) == 1


def test_train_table_rejects_all_missing_after_alignment():
    feat = pd.DataFrame({"x": [np.nan, np.nan, np.nan], "close": [1.0, 2.0, 3.0]})
    with pytest.raises(AthenaRuntimeError, match="No complete training rows"):
        train_table(feat, target="close", algo="linear")


def test_evaluate_aligns_target_shift():
    feat = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0], "close": [2.0, 4.0, 6.0, 8.0, 10.0]})
    model = train_table(feat, target="close", algo="linear", target_shift=1)
    scores = cmd_evaluate("m", ["feat"], {"target": "close", "metrics": "rmse"}, {"m": model, "feat": feat}, None)
    assert "rmse" in scores
    assert scores["rmse"] >= 0.0
