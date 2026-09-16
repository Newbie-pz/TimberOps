"""Sanitized errors raised at the optional AI integration boundary."""


class AIIntegrationError(RuntimeError):
    """Base class whose text is safe to expose through the public API."""

    public_message = "AI service request failed"

    def __init__(self) -> None:
        super().__init__(self.public_message)


class AIServiceUnavailableError(AIIntegrationError):
    """The AI endpoint was called while its provider is unavailable."""

    public_message = "AI service is unavailable"


class AIUpstreamTimeoutError(AIIntegrationError):
    """The provider or the overall Agent execution exceeded its deadline."""

    public_message = "AI upstream service timed out"


class AIUpstreamError(AIIntegrationError):
    """The provider returned a non-timeout transport or API error."""

    public_message = "AI upstream service is temporarily unavailable"


class AIAgentError(AIIntegrationError):
    """The local Agent graph failed independently of its provider."""

    public_message = "AI agent failed to process the request"
