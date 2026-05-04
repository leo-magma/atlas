"""Athena DSL interpreter."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from atlas.parser import tokenize

from . import commands
from .errors import AthenaError, AthenaSyntaxError
from .io.load import load_object
from .io.save import save_object
from .parser import parse_line


def _kw(tokens: list[str], key: str) -> str | None:
    prefix = f"{key}="
    for t in tokens:
        if t.startswith(prefix):
            return t[len(prefix) :]
    return None


class AthenaInterpreter:
    """Execute ``.ath`` scripts (v0)."""

    def __init__(self) -> None:
        self.env: dict[str, Any] = {}
        self._base_dir: str | None = None

    def _run_export(self, tokens: list[str]) -> None:
        if len(tokens) < 2:
            raise AthenaSyntaxError("export requires: export NAME to=PATH")
        name = tokens[1]
        path = _kw(tokens, "to")
        if not path:
            raise AthenaSyntaxError("export requires to=PATH")
        val = self.env[name]
        resolved = self._resolve(path)
        if isinstance(val, pd.DataFrame):
            val.to_csv(resolved, index=True)
        elif isinstance(val, pd.Series):
            val.to_csv(resolved, index=True)
        else:
            raise AthenaError(f"export: cannot serialize type {type(val).__name__}")

    def _run_save(self, tokens: list[str]) -> None:
        if len(tokens) < 3:
            raise AthenaSyntaxError("save requires: save VARNAME to=PATH")
        var = tokens[1]
        path = _kw(tokens, "to")
        if not path:
            raise AthenaSyntaxError("save requires to=PATH")
        obj = self.env[var]
        save_object(path, obj, self._base_dir)

    def _run_load(self, tokens: list[str]) -> None:
        if len(tokens) < 3:
            raise AthenaSyntaxError("load requires: load VARNAME from=PATH")
        var = tokens[1]
        path = _kw(tokens, "from")
        if not path:
            raise AthenaSyntaxError("load requires from=PATH")
        self.env[var] = load_object(path, self._base_dir)

    def _resolve(self, path: str) -> str:
        from atlas.runtime import resolve_path

        return resolve_path(path.strip('"').strip("'"), self._base_dir)

    def run_line(self, line: str) -> None:
        raw = line.strip()
        if not raw:
            return
        tokens = tokenize(raw)
        if not tokens:
            return
        if tokens[0] == "export":
            self._run_export(tokens)
            return
        if tokens[0] == "save":
            self._run_save(tokens)
            return
        if tokens[0] == "load" and len(tokens) >= 2 and tokens[1] != "=":
            # load VAR from= — not ``name = load ...``
            if _kw(tokens, "from"):
                self._run_load(tokens)
                return

        cmd = parse_line(raw)
        result = commands.run_command(
            cmd.func,
            cmd.arg,
            list(cmd.args),
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
                except AthenaError as e:
                    raise AthenaError(f"{path}:{lineno}: {e}") from e
