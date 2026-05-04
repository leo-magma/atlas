"""Command-line entrypoint for the ``atlas`` console script and ``python -m atlas``."""

from __future__ import annotations

import argparse
import sys

from atlas import __version__
from atlas.core import AtlasInterpreter
from atlas.errors import AtlasError


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv in (["--version"], ["-V"]):
        print(f"atlas {__version__}")
        return 0

    p = argparse.ArgumentParser(prog="atlas", description="Run Atlas risk DSL scripts.")
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Print version and exit",
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="Run a .atl (Atlas line DSL) script")
    run_p.add_argument("script", help="Path to a .atl script")
    ns = p.parse_args(argv)

    if ns.cmd != "run":
        return 2
    try:
        AtlasInterpreter().run_file(ns.script)
    except AtlasError as e:
        print(f"atlas: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"atlas: {e}", file=sys.stderr)
        return 1
    return 0
