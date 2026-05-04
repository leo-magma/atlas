"""Console entry for Chronos."""

from __future__ import annotations

import argparse
import sys

from atlas import __version__

from .core import ChronosInterpreter
from .errors import ChronosError


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv in (["--version"], ["-V"]):
        print(f"chronos {__version__}")
        return 0

    p = argparse.ArgumentParser(prog="chronos", description="Run Chronos time-series DSL scripts.")
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Print version and exit",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="Run a .chr script")
    run_p.add_argument("script", help="Path to a .chr script")
    ns = p.parse_args(argv)

    if ns.cmd != "run":
        return 2
    try:
        ChronosInterpreter().run_file(ns.script)
    except ChronosError as e:
        print(f"chronos: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"chronos: {e}", file=sys.stderr)
        return 1
    return 0
