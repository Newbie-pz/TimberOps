"""Select the configured LLM provider at the integration boundary."""

from app.core.config import Settings
from app.integrations.ai.exceptions import AIServiceUnavailableError
from app.integrations.ai.providers.base import LLMProvider
from app.integrations.ai.providers.doubao import DoubaoProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Return the selected provider without initializing a remote client early."""
    if not settings.ai_enabled:
        raise AIServiceUnavailableError
    provider_name = settings.llm_provider.strip().lower()
    if provider_name == "doubao":
        return DoubaoProvider(settings)
    raise AIServiceUnavailableError
