"""Console entry for Neptune."""

from __future__ import annotations

import argparse
import sys

from atlas import __version__

from .core import NeptuneInterpreter
from .errors import NeptuneError


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv in (["--version"], ["-V"]):
        print(f"neptune {__version__}")
        return 0

    p = argparse.ArgumentParser(prog="neptune", description="Run Neptune bond risk DSL scripts.")
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Print version and exit",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="Run a .nep script")
    run_p.add_argument("script", help="Path to a .nep script")
    ns = p.parse_args(argv)

    if ns.cmd != "run":
        return 2
    try:
        NeptuneInterpreter().run_file(ns.script)
    except NeptuneError as e:
        print(f"neptune: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"neptune: {e}", file=sys.stderr)
        return 1
    return 0
