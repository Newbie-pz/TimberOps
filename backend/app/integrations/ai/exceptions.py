"""Errors raised by the optional AI integration boundary."""


class AIServiceUnavailableError(RuntimeError):
    """The AI endpoint was called while its provider is unavailable."""
