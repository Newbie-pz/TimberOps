"""FastAPI dependency wiring for the optional Agent integration."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.integrations.ai.agent.graph import TimberOpsAgent
from app.integrations.ai.providers.factory import create_llm_provider
from app.integrations.ai.tools.weighing_tools import build_weighing_tools
from app.services.analytics_service import AnalyticsService


def get_ai_agent(
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TimberOpsAgent:
    """Build a request-scoped graph; validate provider settings only on AI calls."""
    provider = create_llm_provider(settings)
    tools = build_weighing_tools(AnalyticsService(session))
    return TimberOpsAgent(provider.create_chat_model(), tools)
