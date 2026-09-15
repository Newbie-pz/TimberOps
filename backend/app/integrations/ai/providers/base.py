"""Replaceable chat-model provider contract."""

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel


class LLMProvider(ABC):
    """Create a tool-capable chat model without exposing vendor details."""

    @abstractmethod
    def create_chat_model(self) -> BaseChatModel:
        """Return a configured chat model that supports ``bind_tools``."""
        raise NotImplementedError
