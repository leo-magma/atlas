"""Atlas — a small DSL for financial risk scripting."""

from .core import AtlasInterpreter
from .errors import (
    AtlasError,
    AtlasRuntimeError,
    AtlasSyntaxError,
    UnknownFunctionError,
    UnknownVariableError,
)

__version__ = "0.1.0"

__all__ = [
    "AtlasInterpreter",
    "AtlasError",
    "AtlasRuntimeError",
    "AtlasSyntaxError",
    "UnknownFunctionError",
    "UnknownVariableError",
    "__version__",
]
