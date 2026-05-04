"""Atlas DSL error types."""


class AtlasError(Exception):
    """Base class for Atlas DSL errors."""


class AtlasSyntaxError(AtlasError):
    """Raised when a script line cannot be parsed."""


class AtlasRuntimeError(AtlasError):
    """Raised when execution fails (I/O, missing binding, invalid data)."""


class UnknownFunctionError(AtlasRuntimeError):
    """Raised when a function name is not registered."""


class UnknownVariableError(AtlasRuntimeError):
    """Raised when a referenced variable is not in the environment."""
