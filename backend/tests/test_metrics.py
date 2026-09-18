"""Prometheus endpoint and safe metric instrumentation tests."""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import CargoType, VehicleType
from app.domain.exceptions import BusinessRuleError
from app.main import create_app
from app.models.user import User
from app.observability.metrics import (
    AI_LATENCY_SECONDS,
    AI_REQUESTS_TOTAL,
    BILLING_AMOUNT_TOTAL,
    BILLING_RECORDS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    METRICS_REGISTRY,
    WEIGHING_COMPLETED_TOTAL,
    observe_ai_request,
)
from app.schemas.vehicle import VehicleCreate
from app.schemas.weighing import (
    GrossWeightInput,
    TareWeightInput,
    WeighingTaskCreate,
)
from app.services.billing_service import BillingService
from app.services.vehicle_service import VehicleService
from app.services.weighing_service import WeighingService


TEST_SECRET = "metrics-test-jwt-secret-at-least-32-characters"


def _settings(*, enable_metrics: bool) -> Settings:
    return Settings(
        APP_ENV="test",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        JWT_SECRET_KEY=TEST_SECRET,
        ENABLE_METRICS=enable_metrics,
    )


def _value(name: str, labels: dict[str, str] | None = None) -> float:
    value = METRICS_REGISTRY.get_sample_value(name, labels)
    return float(value or 0)


def test_metrics_endpoint_and_http_metrics(api_client: TestClient) -> None:
    before = _value(
        "timberops_http_requests_total",
        {"method": "GET", "path": "/health", "status_code": "200"},
    )

    response = api_client.get("/health")
    metrics = api_client.get("/metrics")

    assert response.status_code == 200
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    assert _value(
        "timberops_http_requests_total",
        {"method": "GET", "path": "/health", "status_code": "200"},
    ) == before + 1
    assert "timberops_http_request_duration_seconds_bucket" in metrics.text
    assert "timberops_db_pool_checked_out" in metrics.text
    assert "timberops_db_pool_size" in metrics.text
    assert HTTP_REQUESTS_TOTAL is not None
    assert HTTP_REQUEST_DURATION_SECONDS is not None


def test_metrics_endpoint_can_be_disabled() -> None:
    application = create_app(_settings(enable_metrics=False))

    with TestClient(application) as client:
        response = client.get("/metrics")

    assert response.status_code == 404


def test_ai_metrics_increment_without_payload_labels() -> None:
    labels = {"provider": "test-provider", "status": "success"}
    before_requests = _value("timberops_ai_requests_total", labels)
    before_latency_count = _value("timberops_ai_latency_seconds_count")

    observe_ai_request(
        provider="test-provider",
        status="success",
        duration_seconds=0.125,
    )

    assert _value("timberops_ai_requests_total", labels) == before_requests + 1
    assert _value("timberops_ai_latency_seconds_count") == before_latency_count + 1
    assert AI_REQUESTS_TOTAL is not None
    assert AI_LATENCY_SECONDS is not None


def test_committed_weighing_and_billing_metrics(db_session: Session) -> None:
    completed_before = _value("timberops_weighing_completed_total")
    billing_before = _value(
        "timberops_billing_records_total", {"status": "UNPAID"}
    )
    amount_count_before = _value("timberops_billing_amount_total_count")
    paid_before = _value(
        "timberops_billing_records_total", {"status": "PAID"}
    )

    vehicle = VehicleService(db_session).create_vehicle(
        VehicleCreate(
            plate_number="METRICS-001",
            vehicle_type=VehicleType.MEDIUM,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
    )
    service = WeighingService(db_session)
    task = service.create_task(
        WeighingTaskCreate(vehicle_id=vehicle.id, cargo_type=CargoType.TIMBER)
    )
    service.record_tare(task.id, TareWeightInput(weight_tons=Decimal("10.000")))
    service.prepare_for_gross(task.id)
    service.record_gross(task.id, GrossWeightInput(weight_tons=Decimal("40.000")))
    completed = service.complete_task(task.id)

    operator = User(
        username="metrics_operator",
        password_hash="not-used",
        real_name="Metrics Operator",
    )
    db_session.add(operator)
    db_session.commit()
    assert completed.billing_record is not None
    billing_service = BillingService(db_session)
    billing_service.mark_paid(completed.billing_record.id, operator_id=operator.id)
    billing_service.mark_paid(completed.billing_record.id, operator_id=operator.id)

    assert _value("timberops_weighing_completed_total") == completed_before + 1
    assert _value(
        "timberops_billing_records_total", {"status": "UNPAID"}
    ) == billing_before + 1
    assert _value("timberops_billing_amount_total_count") == amount_count_before + 1
    assert _value(
        "timberops_billing_records_total", {"status": "PAID"}
    ) == paid_before + 1
    assert BILLING_RECORDS_TOTAL is not None
    assert BILLING_AMOUNT_TOTAL is not None
    assert WEIGHING_COMPLETED_TOTAL is not None


def test_failed_completion_does_not_increment_business_metrics(
    db_session: Session,
) -> None:
    completed_before = _value("timberops_weighing_completed_total")
    billing_before = _value(
        "timberops_billing_records_total", {"status": "UNPAID"}
    )
    vehicle = VehicleService(db_session).create_vehicle(
        VehicleCreate(
            plate_number="METRICS-FAILED",
            vehicle_type=VehicleType.SMALL,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
    )
    service = WeighingService(db_session)
    task = service.create_task(
        WeighingTaskCreate(vehicle_id=vehicle.id, cargo_type=CargoType.ORE)
    )

    with pytest.raises(BusinessRuleError):
        service.complete_task(task.id)

    assert _value("timberops_weighing_completed_total") == completed_before
    assert _value(
        "timberops_billing_records_total", {"status": "UNPAID"}
    ) == billing_before


def test_metrics_do_not_expose_request_secrets_or_business_identifiers(
    api_client: TestClient,
) -> None:
    token = "jwt-sensitive-value"
    password = "password-sensitive-value"
    plate = "MONG-H-SENSITIVE"
    customer = "customer-sensitive-value"
    prompt = "ai-prompt-sensitive-value"
    missing_vehicle_id = str(uuid4())

    response = api_client.get(
        f"/not-found/{plate}",
        params={"password": password, "customer": customer, "prompt": prompt},
        headers={"Authorization": f"Bearer {token}"},
    )
    vehicle_response = api_client.get(
        f"/api/v1/vehicles/{missing_vehicle_id}",
    )
    metrics = api_client.get("/metrics")

    assert response.status_code == 404
    assert vehicle_response.status_code == 404
    assert _value(
        "timberops_http_requests_total",
        {"method": "GET", "path": "__unmatched__", "status_code": "404"},
    ) >= 1
    assert _value(
        "timberops_http_requests_total",
        {
            "method": "GET",
            "path": "/api/v1/vehicles/{vehicle_id}",
            "status_code": "404",
        },
    ) >= 1
    for sensitive_value in (
        token,
        password,
        plate,
        customer,
        prompt,
        missing_vehicle_id,
    ):
        assert sensitive_value not in metrics.text
