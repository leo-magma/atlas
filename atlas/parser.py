"""Tokenizer and parser for Atlas DSL lines."""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from .errors import AtlasSyntaxError


@dataclass(frozen=True)
class Command:
    """Parsed command: assignment ``name = func ...`` or ``print name``."""

    name: str | None
    func: str
    arg: str | None
    args: list[str]
    kwargs: dict[str, str]


def tokenize(line: str) -> list[str]:
    """Split a line into tokens; supports double-quoted strings and ``#`` comments."""
    if "#" in line:
        line = line.split("#", 1)[0]
    line = line.strip()
    if not line:
        return []
    try:
        return shlex.split(line, posix=True)
    except ValueError as e:
        raise AtlasSyntaxError(str(e)) from e


def _parse_kwargs_and_args(tokens: list[str], start: int) -> tuple[list[str], dict[str, str]]:
    args: list[str] = []
    kwargs: dict[str, str] = {}
    i = start
    while i < len(tokens):
        tok = tokens[i]
        if "=" in tok and tok != "=":
            key, _, value = tok.partition("=")
            if not key:
                raise AtlasSyntaxError(f"Invalid keyword token: {tok!r}")
            kwargs[key] = value
            i += 1
            continue
        if i + 2 < len(tokens) and tokens[i + 1] == "=":
            kwargs[tok] = tokens[i + 2]
            i += 3
            continue
        args.append(tok)
        i += 1
    return args, kwargs


def parse(tokens: list[str]) -> Command:
    """Parse tokens into a :class:`Command`."""
    if not tokens:
        raise AtlasSyntaxError("Empty statement")

    if tokens[0] == "print":
        if len(tokens) < 2:
            raise AtlasSyntaxError("print requires a variable name")
        target = tokens[1]
        extra_args, extra_kwargs = _parse_kwargs_and_args(tokens, 2)
        return Command(name=None, func="print", arg=target, args=extra_args, kwargs=extra_kwargs)

    if len(tokens) < 4 or tokens[1] != "=":
        raise AtlasSyntaxError(
            "Expected ``name = func arg ...`` or ``print name``"
        )

    name, _, func, *rest = tokens
    if not rest:
        raise AtlasSyntaxError(f"Missing argument for {func!r}")

    primary, *tail = rest
    pos_args, kwargs = _parse_kwargs_and_args(tail, 0)
    return Command(name=name, func=func, arg=primary, args=pos_args, kwargs=kwargs)
