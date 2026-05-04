import pytest

from atlas.commands import run_command
from atlas.errors import UnknownFunctionError


def test_load_select_returns_roundtrip(tmp_path):
    csv = tmp_path / "p.csv"
    csv.write_text("date,close\n2024-01-01,100\n2024-01-02,101\n", encoding="utf-8")
    env: dict = {}
    base = str(tmp_path)

    df = run_command("load", str(csv.name), [], {}, env, base)
    env["prices"] = df
    out = run_command("select", "prices", [], {"column": "close"}, env, base)
    env["close"] = out
    rets = run_command("returns", "close", [], {"method": "simple"}, env, base)
    assert len(rets) == 1
    assert rets.iloc[0, 0] == pytest.approx(0.01)


def test_unknown_function():
    with pytest.raises(UnknownFunctionError):
        run_command("nope", "x", [], {}, {}, None)
