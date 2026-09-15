"""Doubao integration through Volcano Ark's OpenAI-compatible endpoint."""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.ai.exceptions import AIServiceUnavailableError
from app.integrations.ai.providers.base import LLMProvider


class DoubaoProvider(LLMProvider):
    """Build the configured Doubao model only when the AI endpoint is called."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_chat_model(self) -> BaseChatModel:
        missing = [
            name
            for name, value in (
                ("DOUBAO_API_KEY", self._settings.doubao_api_key),
                ("DOUBAO_BASE_URL", self._settings.doubao_base_url),
                ("DOUBAO_MODEL", self._settings.doubao_model),
            )
            if not value
        ]
        if missing:
            raise AIServiceUnavailableError(
                "Doubao is not configured; missing: " + ", ".join(missing)
            )

        return ChatOpenAI(
            api_key=SecretStr(self._settings.doubao_api_key or ""),
            base_url=self._settings.doubao_base_url,
            model=self._settings.doubao_model or "",
            temperature=self._settings.ai_temperature,
        )
