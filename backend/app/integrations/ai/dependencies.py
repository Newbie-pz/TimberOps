"""FastAPI dependency wiring for the optional Agent integration."""

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.integrations.ai.agent.graph import TimberOpsAgent
from app.integrations.ai.providers.factory import create_llm_provider
from app.integrations.ai.tools.weighing_tools import (
    SessionFactory,
    build_weighing_tools,
)


def get_ai_tool_session_factory() -> SessionFactory:
    """Return the factory used only inside individual AI Tool executions."""
    return SessionLocal


def get_ai_agent(
    settings: Settings = Depends(get_settings),
    session_factory: SessionFactory = Depends(get_ai_tool_session_factory),
) -> TimberOpsAgent:
    """Build an Agent without borrowing the FastAPI request database session."""
    provider = create_llm_provider(settings)
    tools = build_weighing_tools(session_factory)
    return TimberOpsAgent(provider.create_chat_model(), tools)
