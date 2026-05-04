from pathlib import Path

import pytest

from athena.core import AthenaInterpreter

ROOT = Path(__file__).resolve().parents[1]

pytest.importorskip("sklearn")
pytest.importorskip("joblib")


def test_athena_stock_prediction_example_runs():
    path = ROOT / "athena" / "examples" / "stock_prediction.ath"
    AthenaInterpreter().run_file(str(path))


def test_athena_vol_forecast_example_runs():
    path = ROOT / "athena" / "examples" / "vol_forecast.ath"
    AthenaInterpreter().run_file(str(path))


def test_athena_bond_spread_example_runs():
    path = ROOT / "athena" / "examples" / "bond_spread.ath"
    AthenaInterpreter().run_file(str(path))


def test_athena_save_load_model_roundtrip(tmp_path):
    script = tmp_path / "t.ath"
    model_path = tmp_path / "m.pkl"
    prices = ROOT / "examples" / "prices.csv"
    script.write_text(
        "\n".join(
            [
                f'ts = load "{prices.as_posix()}"',
                "feat = features ts methods=rolling_mean",
                "model = train feat target=close algo=linear",
                f'save model to="{model_path.as_posix()}"',
                f'load model from="{model_path.as_posix()}"',
                "pred = predict model feat",
                "print pred",
            ]
        ),
        encoding="utf-8",
    )
    AthenaInterpreter().run_file(str(script))


def test_athena_backtest_walk_forward_runs(tmp_path):
    script = tmp_path / "bt.ath"
    prices = ROOT / "examples" / "prices.csv"
    script.write_text(
        "\n".join(
            [
                f'ts = load "{prices.as_posix()}"',
                "feat = features ts methods=rolling_mean",
                "s = backtest feat target=close algo=linear folds=2 min_train=10 target_shift=1 metrics=rmse,r2",
                "print s",
            ]
        ),
        encoding="utf-8",
    )
    AthenaInterpreter().run_file(str(script))
