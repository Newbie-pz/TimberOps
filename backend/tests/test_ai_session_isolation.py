"""AI Tool database sessions are isolated from FastAPI request sessions."""

from collections.abc import Callable
from pathlib import Path
from threading import Lock
from time import monotonic, sleep
from typing import Any

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool
import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.integrations.ai.dependencies import get_ai_tool_session_factory
from app.integrations.ai.tools.weighing_tools import build_weighing_tools
from app.main import app
from app.services.analytics_service import AnalyticsService


class SessionTracker:
    """Thread-safe counters for sessions opened and closed by Agent tools."""

    def __init__(self) -> None:
        self.opened = 0
        self.closed = 0
        self._lock = Lock()

    def record_open(self) -> None:
        with self._lock:
            self.opened += 1

    def record_close(self) -> None:
        with self._lock:
            self.closed += 1


def tracking_session_factory(
    engine: Engine,
    tracker: SessionTracker,
) -> Callable[[], Session]:
    """Create normal SQLAlchemy sessions instrumented only for tests."""

    class TrackingSession(Session):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self._close_recorded = False
            tracker.record_open()

        def close(self) -> None:
            if not self._close_recorded:
                self._close_recorded = True
                tracker.record_close()
            super().close()

    return sessionmaker(
        bind=engine,
        class_=TrackingSession,
        expire_on_commit=False,
    )


def tools_by_name(tools: list[BaseTool]) -> dict[str, BaseTool]:
    return {item.name: item for item in tools}


def test_all_ai_tools_query_and_close_their_own_session(
    db_engine: Engine,
) -> None:
    tracker = SessionTracker()
    tools = tools_by_name(
        build_weighing_tools(tracking_session_factory(db_engine, tracker))
    )

    results = [
        tools["get_today_weighing_summary"].invoke({}),
        tools["get_cargo_weight_summary"].invoke({"cargo_type": "COAL"}),
        tools["get_overweight_records"].invoke({}),
        tools["get_vehicle_weighing_history"].invoke(
            {"plate_number": "蒙H00000"}
        ),
        tools["get_weighing_task_detail"].invoke({"task_no": "WT-NOT-FOUND"}),
    ]

    assert len(results) == 5
    assert tracker.opened == 5
    assert tracker.closed == 5


def test_twenty_tool_calls_do_not_exhaust_queue_pool(tmp_path: Path) -> None:
    engine = create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'ai-tools.db').as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
        pool_size=1,
        max_overflow=0,
        pool_timeout=0.1,
    )
    Base.metadata.create_all(engine)
    tracker = SessionTracker()
    tool = tools_by_name(
        build_weighing_tools(tracking_session_factory(engine, tracker))
    )["get_today_weighing_summary"]

    try:
        for _ in range(20):
            result = tool.invoke({})
            assert result["completed_tasks"] == 0

        assert tracker.opened == 20
        assert tracker.closed == 20
        assert engine.pool.checkedout() == 0
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


class ToolCallingModel:
    """Request one real Tool call, then return a deterministic answer."""

    def __init__(self) -> None:
        self.calls = 0

    def bind_tools(self, tools: list[BaseTool]) -> "ToolCallingModel":
        assert "get_today_weighing_summary" in {item.name for item in tools}
        return self

    async def ainvoke(self, messages: list[BaseMessage]) -> AIMessage:
        del messages
        self.calls += 1
        if self.calls == 1:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_today_weighing_summary",
                        "args": {},
                        "id": "isolated-session-call",
                        "type": "tool_call",
                    }
                ],
            )
        return AIMessage(content="查询完成。")


class StubProvider:
    def create_chat_model(self) -> ToolCallingModel:
        return ToolCallingModel()


def enabled_test_settings(*, agent_timeout: float = 1) -> Settings:
    return Settings(
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        AI_ENABLED=True,
        LLM_TIMEOUT_SECONDS=0.01,
        AI_AGENT_TIMEOUT_SECONDS=agent_timeout,
    )


def install_agent_overrides(
    monkeypatch: pytest.MonkeyPatch,
    factory: Callable[[], Session],
    settings: Settings,
) -> Callable[[], object] | None:
    """Install a fake model while retaining the production Agent and Tool graph."""
    monkeypatch.setattr(
        "app.integrations.ai.dependencies.create_llm_provider",
        lambda _: StubProvider(),
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_ai_tool_session_factory] = lambda: factory
    previous_get_db = app.dependency_overrides.get(get_db)

    def forbidden_request_session() -> None:
        raise AssertionError("AI endpoint must not resolve Depends(get_db)")

    app.dependency_overrides[get_db] = forbidden_request_session
    return previous_get_db


def clear_agent_overrides(previous_get_db: Callable[[], object] | None) -> None:
    app.dependency_overrides.pop(get_settings, None)
    app.dependency_overrides.pop(get_ai_tool_session_factory, None)
    if previous_get_db is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous_get_db


def test_ai_request_uses_no_fastapi_request_session(
    api_client: TestClient,
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracker = SessionTracker()
    factory = tracking_session_factory(db_engine, tracker)
    previous_get_db = install_agent_overrides(
        monkeypatch,
        factory,
        enabled_test_settings(),
    )
    try:
        response = api_client.post(
            "/api/v1/ai/chat",
            json={"message": "今天煤炭称了多少吨？"},
        )
    finally:
        clear_agent_overrides(previous_get_db)

    assert response.status_code == 200
    assert response.json()["answer"] == "查询完成。"
    assert tracker.opened == 1
    assert tracker.closed == 1


def test_agent_timeout_does_not_close_a_session_still_used_by_tool_thread(
    api_client: TestClient,
    db_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracker = SessionTracker()
    factory = tracking_session_factory(db_engine, tracker)
    original_query = AnalyticsService.get_today_weighing_summary

    def slow_query(service: AnalyticsService) -> dict[str, Any]:
        sleep(0.2)
        return original_query(service)

    monkeypatch.setattr(
        AnalyticsService,
        "get_today_weighing_summary",
        slow_query,
    )
    previous_get_db = install_agent_overrides(
        monkeypatch,
        factory,
        enabled_test_settings(agent_timeout=0.05),
    )
    try:
        response = api_client.post(
            "/api/v1/ai/chat",
            json={"message": "今天煤炭称了多少吨？"},
        )
        deadline = monotonic() + 1
        while tracker.closed < 1 and monotonic() < deadline:
            sleep(0.01)
    finally:
        clear_agent_overrides(previous_get_db)

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "AI_UPSTREAM_TIMEOUT"
    assert "IllegalStateChangeError" not in response.text
    assert tracker.opened == 1
    assert tracker.closed == 1
