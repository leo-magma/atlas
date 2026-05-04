from pathlib import Path

from atlas.core import AtlasInterpreter

ROOT = Path(__file__).resolve().parents[1]


def test_run_example_scripts():
    for name in ("example1.risk", "example2.risk", "example3.risk"):
        AtlasInterpreter().run_file(str(ROOT / "examples" / name))
