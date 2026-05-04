"""Run with: ``python -m atlas run path/to/script.atl`` (same as the ``atlas`` console command)."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
