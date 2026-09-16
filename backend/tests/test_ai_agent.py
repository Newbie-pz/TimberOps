"""Agent reliability tests that never call a real external model."""

import asyncio
import logging
from time import perf_counter
from typing import Any
from uuid import UUID

import httpx2
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_openai.chat_models.base import OpenAIConnectionError, OpenAITimeoutError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.ai.agent.graph import AgentResult, TimberOpsAgent, ToolCallTrace
from app.integrations.ai.dependencies import get_ai_agent
from app.integrations.ai.providers.doubao import DoubaoProvider
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

    async def ainvoke(self, messages: list[BaseMessage]) -> AIMessage:
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
    UUID(response.headers["X-Request-ID"])
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


def test_mock_agent_executes_tool_and_receives_structured_result(
    db_session: Session,
) -> None:
    model = StubToolCallingModel()
    tools = build_weighing_tools(AnalyticsService(db_session))
    agent = TimberOpsAgent(model, tools)

    result = asyncio.run(agent.achat("今天有多少称重任务？"))

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
    async def achat(self, message: str) -> Any:
        del message
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
    app.dependency_overrides[get_ai_agent] = lambda: StubAgent()
    try:
        response = api_client.post(
            "/api/v1/ai/chat",
            json={"message": "今天煤炭称了多少吨？"},
        )
    finally:
        app.dependency_overrides.pop(get_ai_agent, None)

    assert response.status_code == 200
    UUID(response.headers["X-Request-ID"])
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


class SleepingAgent:
    async def achat(self, message: str) -> AgentResult:
        del message
        await asyncio.sleep(0.2)
        return AgentResult(answer="too late", tool_calls=[])


class FailingAgent:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def achat(self, message: str) -> AgentResult:
        del message
        raise self.error


def _enabled_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "AI_ENABLED": True,
        "LLM_PROVIDER": "doubao",
        "DOUBAO_API_KEY": "test-api-key-never-log",
        "DOUBAO_BASE_URL": "https://example.invalid/v1",
        "DOUBAO_MODEL": "test-model",
        "LLM_TIMEOUT_SECONDS": 0.01,
        "AI_AGENT_TIMEOUT_SECONDS": 0.05,
    }
    values.update(overrides)
    return Settings(**values)


def _post_with_agent(
    api_client: TestClient,
    agent: object,
    *,
    settings: Settings | None = None,
) -> Any:
    app.dependency_overrides[get_ai_agent] = lambda: agent
    app.dependency_overrides[get_settings] = lambda: settings or _enabled_settings()
    try:
        return api_client.post(
            "/api/v1/ai/chat",
            json={"message": "private business question"},
        )
    finally:
        app.dependency_overrides.pop(get_ai_agent, None)
        app.dependency_overrides.pop(get_settings, None)


def test_agent_overall_timeout_returns_504_promptly(api_client: TestClient) -> None:
    started = perf_counter()
    response = _post_with_agent(api_client, SleepingAgent())
    elapsed = perf_counter() - started

    assert elapsed < 0.2
    assert response.status_code == 504
    assert response.json() == {
        "error": {
            "code": "AI_UPSTREAM_TIMEOUT",
            "message": "AI upstream service timed out",
        }
    }


def test_provider_timeout_is_mapped_to_504(api_client: TestClient) -> None:
    error = OpenAITimeoutError(httpx2.Request("POST", "https://example.invalid"))
    response = _post_with_agent(api_client, FailingAgent(error))

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "AI_UPSTREAM_TIMEOUT"


def test_upstream_error_is_safe_and_logged_without_secrets(
    api_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "test-api-key-never-log"
    error = OpenAIConnectionError(
        message=f"Authorization Bearer {secret}; upstream body System Prompt",
        request=httpx2.Request("POST", "https://example.invalid"),
    )
    with caplog.at_level(logging.INFO, logger="timberops.ai"):
        response = _post_with_agent(api_client, FailingAgent(error))

    serialized = response.text + caplog.text
    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "AI_UPSTREAM_ERROR",
            "message": "AI upstream service is temporarily unavailable",
        }
    }
    assert secret not in serialized
    assert "System Prompt" not in serialized
    assert "Traceback" not in serialized
    assert "request_id=" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "success=False" in caplog.text


def test_unexpected_agent_error_returns_safe_500(api_client: TestClient) -> None:
    response = _post_with_agent(
        api_client,
        FailingAgent(RuntimeError("database_url=postgresql://secret")),
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "AI_AGENT_ERROR",
            "message": "AI agent failed to process the request",
        }
    }
    assert "postgresql" not in response.text


def test_request_ids_are_unique(api_client: TestClient) -> None:
    first = _post_with_agent(api_client, StubAgent())
    second = _post_with_agent(api_client, StubAgent())

    first_id = first.headers["X-Request-ID"]
    second_id = second.headers["X-Request-ID"]
    UUID(first_id)
    UUID(second_id)
    assert first_id != second_id


def test_success_log_contains_duration_and_tool_names(
    api_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="timberops.ai"):
        response = _post_with_agent(api_client, StubAgent())

    assert response.status_code == 200
    assert "request_id=" in caplog.text
    assert "duration_ms=" in caplog.text
    assert "success=True" in caplog.text
    assert "get_today_weighing_summary" in caplog.text
    assert "private business question" not in caplog.text


def test_provider_receives_timeout_and_retry_settings() -> None:
    settings = _enabled_settings(
        LLM_TIMEOUT_SECONDS=4,
        AI_AGENT_TIMEOUT_SECONDS=5,
        LLM_MAX_RETRIES=1,
    )
    model = DoubaoProvider(settings).create_chat_model()

    assert model.request_timeout == 4
    assert model.max_retries == 1


def test_settings_reject_provider_timeout_outside_agent_budget() -> None:
    with pytest.raises(ValidationError, match="LLM_TIMEOUT_SECONDS must be less"):
        Settings(LLM_TIMEOUT_SECONDS=30, AI_AGENT_TIMEOUT_SECONDS=30)
