"""Agent graph and API tests that never call a real external model."""

from typing import Any

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.ai.agent.graph import TimberOpsAgent
from app.integrations.ai.tools.weighing_tools import build_weighing_tools
from app.main import app
from app.services.analytics_service import AnalyticsService


class StubToolCallingModel:
    """Two-turn model: request one tool, then answer from its ToolMessage."""

    def __init__(self) -> None:
        self.calls = 0
        self.bound_tool_names: list[str] = []
        self.received_tool_message: ToolMessage | None = None

    def bind_tools(self, tools: list[BaseTool]) -> "StubToolCallingModel":
        self.bound_tool_names = [item.name for item in tools]
        return self

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_today_weighing_summary",
                        "args": {},
                        "id": "call-summary",
                        "type": "tool_call",
                    }
                ],
            )
        self.received_tool_message = next(
            message
            for message in messages
            if isinstance(message, ToolMessage)
        )
        return AIMessage(content="今天完成 0 个称重任务，总净重 0.000 t。")


def test_ai_disabled_returns_unified_503_and_health_still_works(
    api_client: TestClient,
) -> None:
    disabled_settings = Settings(
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        AI_ENABLED=False,
    )
    app.dependency_overrides[get_settings] = lambda: disabled_settings
    try:
        response = api_client.post(
            "/api/v1/ai/chat",
            json={"message": "今天有多少称重任务？"},
        )
        health = api_client.get("/health")
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_SERVICE_UNAVAILABLE"
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


def test_mock_agent_executes_tool_and_receives_structured_result(
    db_session: Session,
) -> None:
    model = StubToolCallingModel()
    tools = build_weighing_tools(AnalyticsService(db_session))
    agent = TimberOpsAgent(model, tools)

    result = agent.chat("今天有多少称重任务？")

    assert "get_today_weighing_summary" in model.bound_tool_names
    assert model.received_tool_message is not None
    assert '"completed_tasks": 0' in str(model.received_tool_message.content)
    assert result.answer == "今天完成 0 个称重任务，总净重 0.000 t。"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "get_today_weighing_summary"
    assert result.tool_calls[0].arguments == {}
    assert result.tool_calls[0].status == "completed"


def test_ai_enabled_without_doubao_configuration_returns_503(
    api_client: TestClient,
) -> None:
    incomplete_settings = Settings(
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        AI_ENABLED=True,
        LLM_PROVIDER="doubao",
        DOUBAO_API_KEY="",
        DOUBAO_BASE_URL="",
        DOUBAO_MODEL="",
    )
    app.dependency_overrides[get_settings] = lambda: incomplete_settings
    try:
        response = api_client.post(
            "/api/v1/ai/chat",
            json={"message": "今天有多少称重任务？"},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_SERVICE_UNAVAILABLE"


class StubAgent:
    def chat(self, message: str) -> Any:
        del message
        from app.integrations.ai.agent.graph import AgentResult, ToolCallTrace

        return AgentResult(
            answer="查询完成。",
            tool_calls=[
                ToolCallTrace(
                    name="get_today_weighing_summary",
                    arguments={},
                    status="completed",
                )
            ],
        )


def test_agent_api_returns_safe_tool_trace(api_client: TestClient) -> None:
    from app.integrations.ai.dependencies import get_ai_agent

    app.dependency_overrides[get_ai_agent] = lambda: StubAgent()
    try:
        response = api_client.post(
            "/api/v1/ai/chat",
            json={"message": "今天煤炭称了多少吨？"},
        )
    finally:
        app.dependency_overrides.pop(get_ai_agent, None)

    assert response.status_code == 200
    assert response.json() == {
        "answer": "查询完成。",
        "tool_calls": [
            {
                "name": "get_today_weighing_summary",
                "arguments": {},
                "status": "completed",
            }
        ],
    }
