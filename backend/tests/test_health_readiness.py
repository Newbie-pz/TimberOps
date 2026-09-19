"""Liveness, readiness, and diagnostic data-safety tests."""

from collections.abc import Generator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool, StaticPool

from app.api.router import get_readiness_service
from app.main import app
from app.observability.health import ReadinessService, readiness_connection


EXPECTED_HEAD = "expected_test_revision"


@pytest.fixture
def revision_engine() -> Generator[Engine, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": EXPECTED_HEAD},
        )
    yield engine
    engine.dispose()


@contextmanager
def _client_with_service(
    service: ReadinessService,
) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_readiness_service] = lambda: service
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_readiness_service, None)


def test_health_is_live_with_database_available(
    revision_engine: Engine,
) -> None:
    service = ReadinessService(
        revision_engine,
        expected_heads=(EXPECTED_HEAD,),
    )
    with _client_with_service(service) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "TimberOps backend",
    }


def test_health_does_not_invoke_database_readiness() -> None:
    class ExplodingService:
        def check(self) -> None:
            raise AssertionError("liveness must not access the database")

    with _client_with_service(ExplodingService()) as client:  # type: ignore[arg-type]
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_when_database_and_revision_match(
    revision_engine: Engine,
) -> None:
    service = ReadinessService(
        revision_engine,
        expected_heads=(EXPECTED_HEAD,),
    )
    with _client_with_service(service) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok", "migration": "ok"},
    }
    assert EXPECTED_HEAD not in response.text


def test_ready_returns_safe_503_when_database_is_unavailable() -> None:
    class UnavailableEngine:
        url = make_url("sqlite+pysqlite:///:memory:")

        def connect(self) -> None:
            raise RuntimeError(
                "DATABASE_URL=postgresql://user:password@secret-host SQL SELECT 1"
            )

    service = ReadinessService(
        UnavailableEngine(),  # type: ignore[arg-type]
        expected_heads=(EXPECTED_HEAD,),
    )
    with _client_with_service(service) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "failed", "migration": "unknown"},
    }
    body = response.text.lower()
    for forbidden in (
        "database_url",
        "password",
        "secret-host",
        "select 1",
        "traceback",
    ):
        assert forbidden not in body


def test_ready_returns_503_when_migration_is_outdated(
    revision_engine: Engine,
) -> None:
    service = ReadinessService(
        revision_engine,
        expected_heads=("newer_code_revision",),
    )
    with _client_with_service(service) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "ok", "migration": "outdated"},
    }


def test_readiness_is_read_only_and_does_not_run_migrations(
    revision_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statements: list[str] = []

    @event.listens_for(revision_engine, "before_cursor_execute")
    def capture_statement(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: object,
    ) -> None:
        statements.append(statement.strip().upper())

    def forbidden_upgrade(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("readiness must never execute migrations")

    monkeypatch.setattr("alembic.command.upgrade", forbidden_upgrade)
    service = ReadinessService(
        revision_engine,
        expected_heads=(EXPECTED_HEAD,),
    )

    result = service.check()

    assert result.is_ready is True
    assert any(statement.startswith("SELECT 1") for statement in statements)
    assert not any(
        statement.startswith(
            ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")
        )
        for statement in statements
    )
    with revision_engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert revision == EXPECTED_HEAD


def test_readiness_does_not_call_ai_or_mcp(
    revision_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_integration(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("readiness must not call optional integrations")

    monkeypatch.setattr(
        "app.integrations.ai.providers.factory.create_llm_provider",
        forbidden_integration,
    )
    monkeypatch.setattr(
        "app.integrations.mcp.server.create_mcp_server",
        forbidden_integration,
    )
    service = ReadinessService(
        revision_engine,
        expected_heads=(EXPECTED_HEAD,),
    )

    with _client_with_service(service) as client:
        response = client.get("/ready")

    assert response.status_code == 200


def test_postgresql_readiness_uses_disposable_fast_probe_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = make_url(
        "postgresql+psycopg://user:password@localhost:5432/timberops"
    )
    connection = object()

    class BusinessEngine:
        url = database_url

        def connect(self) -> None:
            raise AssertionError("readiness must not borrow the business pool")

    class ProbeEngine:
        disposed = False

        @contextmanager
        def connect(self) -> Generator[object, None, None]:
            yield connection

        def dispose(self) -> None:
            self.disposed = True

    probe_engine = ProbeEngine()
    captured: dict[str, object] = {}

    def fake_create_engine(url: object, **kwargs: object) -> ProbeEngine:
        captured["url"] = url
        captured.update(kwargs)
        return probe_engine

    monkeypatch.setattr(
        "app.observability.health.create_engine",
        fake_create_engine,
    )

    with readiness_connection(BusinessEngine()) as actual:  # type: ignore[arg-type]
        assert actual is connection

    assert captured == {
        "url": database_url,
        "poolclass": NullPool,
        "hide_parameters": True,
        "connect_args": {
            "connect_timeout": 2,
            "hostaddr": "127.0.0.1",
        },
    }
    assert probe_engine.disposed is True
