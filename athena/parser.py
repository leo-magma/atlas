"""Athena reuses Atlas line grammar (assignments and ``print``)."""

from __future__ import annotations

from atlas.errors import AtlasSyntaxError
from atlas.parser import Command, parse, tokenize

from .errors import AthenaSyntaxError

__all__ = ["Command", "parse_line", "tokenize"]


def parse_line(line: str) -> Command:
    """Tokenize and parse one line; wrap Atlas syntax errors as :class:`AthenaSyntaxError`."""
    tokens = tokenize(line)
    if not tokens:
        raise AthenaSyntaxError("Empty statement")
    try:
        return parse(tokens)
    except AtlasSyntaxError as e:
        raise AthenaSyntaxError(str(e)) from e
