"""Neptune DSL errors."""


class NeptuneError(Exception):
    """Base error for Neptune scripts."""


class NeptuneSyntaxError(NeptuneError):
    """Invalid line syntax."""


class NeptuneRuntimeError(NeptuneError):
    """Runtime failure."""


class UnknownCommandError(NeptuneRuntimeError):
    """Unknown DSL function."""


class UnknownVariableError(NeptuneRuntimeError):
    """Unknown variable."""
