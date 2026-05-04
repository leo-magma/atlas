"""Chronos DSL errors."""


class ChronosError(Exception):
    """Base error for Chronos scripts."""


class ChronosSyntaxError(ChronosError):
    """Invalid line syntax."""


class ChronosRuntimeError(ChronosError):
    """Runtime failure (I/O, unknown command, invalid frame)."""


class UnknownCommandError(ChronosRuntimeError):
    """Unknown DSL function name."""


class UnknownVariableError(ChronosRuntimeError):
    """Unknown environment binding."""
