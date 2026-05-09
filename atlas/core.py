"""Atlas interpreter: environment, line execution, file runner."""

from __future__ import annotations

import os
from typing import Any

from . import commands, var_blocks
from .errors import AtlasError, AtlasSyntaxError
from .parser import parse, tokenize

_BLOCK_KINDS = frozenset({"model", "validation", "compare"})


def _parse_block_header(stripped: str) -> tuple[str, str] | None:
    if not stripped.endswith(":"):
        return None
    head = stripped[:-1].strip()
    parts = head.split(None, 1)
    if len(parts) != 2:
        return None
    kind, name = parts
    if kind not in _BLOCK_KINDS:
        return None
    return kind, name


class AtlasInterpreter:
    """Execute Atlas ``.atl`` scripts line by line."""

    def __init__(self) -> None:
        self.env: dict[str, Any] = {}
        self._base_dir: str | None = None
        self._block_meta: tuple[str, str] | None = None
        self._block_buffer: list[str] = []

    def _flush_block(self) -> None:
        if self._block_meta is None:
            return
        kind, name = self._block_meta
        self._block_meta = None
        body = self._block_buffer
        self._block_buffer = []
        var_blocks.dispatch_block(kind, name, body, self.env)

    def finalize(self) -> None:
        """Close an open ``model`` / ``validation`` / ``compare`` block (call at EOF)."""
        self._flush_block()

    def run_line(self, line: str) -> None:
        while True:
            if self._block_meta is not None:
                if not line.strip():
                    return
                if line[0] in (" ", "\t"):
                    self._block_buffer.append(line)
                    return
                self._flush_block()
                continue

            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                return
            hdr = _parse_block_header(stripped)
            if hdr is not None:
                kind, name = hdr
                self._block_meta = (kind, name)
                self._block_buffer = []
                return

            tokens = tokenize(line)
            if not tokens:
                return
            cmd = parse(tokens)
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
            return

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
        self.finalize()
