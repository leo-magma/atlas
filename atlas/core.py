"""Atlas interpreter: environment, line execution, file runner."""

from __future__ import annotations

import os
from typing import Any

from . import commands
from .errors import AtlasError, AtlasSyntaxError
from .parser import parse, tokenize


class AtlasInterpreter:
    """Execute Atlas ``.risk`` scripts line by line."""

    def __init__(self) -> None:
        self.env: dict[str, Any] = {}
        self._base_dir: str | None = None

    def run_line(self, line: str) -> None:
        tokens = tokenize(line)
        if not tokens:
            return
        try:
            cmd = parse(tokens)
        except AtlasSyntaxError:
            raise
        result = commands.run_command(
            cmd.func,
            cmd.arg,
            cmd.args,
            dict(cmd.kwargs),
            self.env,
            self._base_dir,
        )
        if cmd.func != "print" and cmd.name is not None:
            self.env[cmd.name] = result

    def run_file(self, path: str) -> None:
        self._base_dir = os.path.dirname(os.path.abspath(path))
        with open(path, encoding="utf-8") as f:
            for lineno, raw in enumerate(f, start=1):
                line = raw.rstrip("\n")
                if not line.strip():
                    continue
                try:
                    self.run_line(line)
                except AtlasError as e:
                    raise AtlasError(f"{path}:{lineno}: {e}") from e
