from pathlib import Path

from atlas.core import AtlasInterpreter

ROOT = Path(__file__).resolve().parents[1]


def test_run_example_scripts():
    for name in (
        "example1.atl",
        "example2.atl",
        "example3.atl",
        "example4.atl",
        "example5.atl",
        "example6.atl",
        "example7.atl",
        "example_portfolio.atl",
        "example_var_validation.atl",
        "atlas_cookbook.atl",
    ):
        AtlasInterpreter().run_file(str(ROOT / "examples" / name))
