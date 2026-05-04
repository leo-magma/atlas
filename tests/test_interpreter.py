from pathlib import Path

from atlas.core import AtlasInterpreter

ROOT = Path(__file__).resolve().parents[1]


def test_run_example_scripts():
    for name in ("example1.atl", "example2.atl", "example3.atl"):
        AtlasInterpreter().run_file(str(ROOT / "examples" / name))
