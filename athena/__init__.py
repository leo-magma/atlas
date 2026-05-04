"""Athena — cross-asset ML layer for the Atlas suite (v0 scaffold)."""

from .core import AthenaInterpreter
from .errors import (
    AthenaError,
    AthenaRuntimeError,
    AthenaSyntaxError,
    UnknownCommandError,
    UnknownVariableError,
)

__version__ = "0.1.0"

__all__ = [
    "AthenaInterpreter",
    "AthenaError",
    "AthenaRuntimeError",
    "AthenaSyntaxError",
    "UnknownCommandError",
    "UnknownVariableError",
    "__version__",
]
