"""Unified HTTP request logging, correlation, and redaction tests."""

import json
import logging
from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.middleware.request_logging import logger as request_logger


TEST_SECRET = "request-logging-test-jwt-secret-at-least-32-characters"


@pytest.fixture(autouse=True)
def capture_request_logger(
    caplog: pytest.LogCaptureFixture,
) -> Generator[None, None, None]:
    request_logger.addHandler(caplog.handler)
    try:
        yield
    finally:
        request_logger.removeHandler(caplog.handler)


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "test",
        "DEBUG": False,
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "JWT_SECRET_KEY": TEST_SECRET,
        "SLOW_REQUEST_THRESHOLD_MS": 1000,
    }
    values.update(overrides)
    return Settings(**values)


def _request_records(
    caplog: pytest.LogCaptureFixture,
) -> list[tuple[logging.LogRecord, dict[str, object]]]:
    return [
        (record, json.loads(record.getMessage()))
        for record in caplog.records
        if record.name == "timberops.http"
    ]


def test_request_id_is_generated_and_returned(
    api_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="timberops.http"):
        response = api_client.get("/health", headers={"Authorization": ""})

    request_id = response.headers["X-Request-ID"]
    UUID(request_id)
    _, payload = _request_records(caplog)[-1]
    assert payload["request_id"] == request_id
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["status_code"] == 200
    assert payload["timestamp"]
    assert payload["client_ip"]


def test_safe_incoming_request_id_is_reused(
    api_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    supplied_id = "gateway-01:request_123"
    with caplog.at_level(logging.INFO, logger="timberops.http"):
        response = api_client.get(
            "/health",
            headers={"X-Request-ID": supplied_id},
        )

    assert response.headers["X-Request-ID"] == supplied_id
    assert _request_records(caplog)[-1][1]["request_id"] == supplied_id


def test_unsafe_incoming_request_id_is_replaced(api_client: TestClient) -> None:
    supplied_id = "x" * 129

    response = api_client.get(
        "/health",
        headers={"X-Request-ID": supplied_id},
    )

    assert response.headers["X-Request-ID"] != supplied_id
    UUID(response.headers["X-Request-ID"])


def test_authenticated_user_claims_are_logged_without_database_lookup(
    api_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="timberops.http"):
        response = api_client.get("/health")

    assert response.status_code == 200
    _, payload = _request_records(caplog)[-1]
    UUID(str(payload["user_id"]))
    assert payload["username"] == "test_admin"


def test_unauthorized_request_never_logs_bearer_token(
    api_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_token = "sensitive-token-must-never-appear"
    with caplog.at_level(logging.INFO, logger="timberops.http"):
        response = api_client.get(
            "/api/v1/vehicles",
            headers={"Authorization": f"Bearer {sensitive_token}"},
        )

    assert response.status_code == 401
    record, payload = _request_records(caplog)[-1]
    assert record.levelno == logging.WARNING
    assert payload["user_id"] is None
    assert payload["username"] is None
    assert sensitive_token not in caplog.text


def test_internal_error_log_and_response_hide_exception_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    application = create_app(_settings())
    sensitive_detail = "password=never-log database_url=private-path"

    @application.get("/__request-logging-error")
    def raise_internal_error() -> None:
        raise RuntimeError(sensitive_detail)

    with TestClient(application, raise_server_exceptions=False) as client:
        with caplog.at_level(logging.INFO):
            response = client.get("/__request-logging-error")

    assert response.status_code == 500
    UUID(response.headers["X-Request-ID"])
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    record, payload = _request_records(caplog)[-1]
    assert record.levelno == logging.ERROR
    assert payload["status_code"] == 500
    assert sensitive_detail not in response.text
    assert sensitive_detail not in caplog.text


def test_slow_request_emits_an_additional_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    application = create_app(_settings(SLOW_REQUEST_THRESHOLD_MS=0))

    with TestClient(application) as client:
        with caplog.at_level(logging.INFO, logger="timberops.http"):
            response = client.get("/health")

    assert response.status_code == 200
    records = _request_records(caplog)
    normal = next(item for item in records if item[1]["event"] == "http_request")
    slow = next(item for item in records if item[1]["event"] == "slow_request")
    assert normal[0].levelno == logging.INFO
    assert slow[0].levelno == logging.WARNING
    assert slow[1]["slow_request_threshold_ms"] == 0
    assert slow[1]["request_id"] == normal[1]["request_id"]
