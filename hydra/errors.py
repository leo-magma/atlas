"""Hydra DSL errors."""


class HydraError(Exception):
    """Base error."""


class HydraSyntaxError(HydraError):
    """Invalid syntax."""


class HydraRuntimeError(HydraError):
    """Runtime failure."""


class UnknownCommandError(HydraRuntimeError):
    """Unknown function."""


class UnknownVariableError(HydraRuntimeError):
    """Unknown variable."""
