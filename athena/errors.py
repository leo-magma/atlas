"""Athena DSL errors."""


class AthenaError(Exception):
    """Base error for Athena execution."""


class AthenaSyntaxError(AthenaError):
    """Invalid Athena script syntax."""


class AthenaRuntimeError(AthenaError):
    """Runtime failure (I/O, ML, missing dependency)."""


class UnknownVariableError(AthenaRuntimeError):
    """Reference to an undefined script variable."""


class UnknownCommandError(AthenaRuntimeError):
    """Unknown DSL verb."""
