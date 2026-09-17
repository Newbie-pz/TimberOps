"""Production configuration, error-envelope, and role-boundary tests."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import CargoType, PaymentStatus, VehicleType, WeighingStatus
from app.main import create_app
from app.models.billing import BillingRecord
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask
from app.security.jwt import create_access_token


TEST_SECRET = "security-hardening-test-key-with-at-least-32-characters"


def _production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "production",
        "DEBUG": False,
        "ENABLE_API_DOCS": False,
        "CORS_ALLOWED_ORIGINS": "https://timberops.example.com",
        "DATABASE_URL": "postgresql+psycopg://timberops:password@db:5432/timberops",
        "JWT_SECRET_KEY": TEST_SECRET,
    }
    values.update(overrides)
    return Settings(**values)


def _headers_for_role(engine: Engine, role_name: str) -> dict[str, str]:
    with Session(engine) as session:
        role = session.scalar(select(Role).where(Role.name == role_name))
        assert role is not None
        username = f"security_{role_name.lower()}"
        user = User(username=username, password_hash="not-used", real_name=username)
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()
        token = create_access_token(user_id=user.id, username=user.username)
    return {"Authorization": f"Bearer {token}"}


def _seed_billing_record(engine: Engine) -> UUID:
    with Session(engine) as session:
        vehicle = Vehicle(
            plate_number="蒙S27001",
            vehicle_type=VehicleType.SMALL,
            allowed_gross_weight_tons=Decimal("20.000"),
        )
        session.add(vehicle)
        session.flush()
        task = WeighingTask(
            task_no="SECURITY-BILLING-001",
            vehicle_id=vehicle.id,
            cargo_type=CargoType.COAL,
            allowed_gross_weight_tons=Decimal("20.000"),
            overweight_tons=Decimal("0.000"),
            status=WeighingStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(task)
        session.flush()
        record = BillingRecord(
            weighing_task_id=task.id,
            vehicle_id=vehicle.id,
            vehicle_type_snapshot=VehicleType.SMALL,
            fee_amount=Decimal("10.00"),
            payment_status=PaymentStatus.UNPAID,
        )
        session.add(record)
        session.commit()
        return record.id


def test_production_rejects_debug_loopback_database_and_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        _production_settings(DEBUG=True)
    with pytest.raises(ValidationError, match="network service host"):
        _production_settings(
            DATABASE_URL="postgresql+psycopg://timberops:password@127.0.0.1/timberops"
        )
    with pytest.raises(ValidationError, match="must not contain a wildcard"):
        _production_settings(CORS_ALLOWED_ORIGINS="*")


def test_placeholder_jwt_secret_is_rejected_even_when_long() -> None:
    settings = Settings(
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        JWT_SECRET_KEY="replace_with_at_least_32_random_characters",
    )

    with pytest.raises(RuntimeError, match="must be replaced"):
        settings.require_jwt_secret_key()


def test_production_docs_are_disabled_and_cors_is_exact() -> None:
    application = create_app(_production_settings())

    with TestClient(application) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        allowed = client.options(
            "/health",
            headers={
                "Origin": "https://timberops.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = client.options(
            "/health",
            headers={
                "Origin": "https://attacker.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.headers["access-control-allow-origin"] == "https://timberops.example.com"
    assert "access-control-allow-credentials" not in allowed.headers
    assert "access-control-allow-origin" not in denied.headers


def test_unhandled_error_returns_sanitized_envelope() -> None:
    application = create_app(_production_settings(CORS_ALLOWED_ORIGINS=""))

    @application.get("/__security-test-error")
    def raise_internal_error() -> None:
        raise RuntimeError("password=secret SQL failed at C:/private/path")

    with TestClient(application, raise_server_exceptions=False) as client:
        response = client.get("/__security-test-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "系统异常，请稍后重试",
        }
    }
    assert "secret" not in response.text
    assert "private" not in response.text


def test_business_reads_require_authentication(api_client: TestClient) -> None:
    for path in (
        "/api/v1/vehicles",
        "/api/v1/customers",
        "/api/v1/weighing/tasks",
        "/api/v1/weighing/cargo-catalog",
    ):
        response = api_client.get(path, headers={"Authorization": ""})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.parametrize("role_name", ["VIEWER", "OPERATOR"])
def test_non_admin_roles_cannot_manage_users_waive_or_delete(
    api_client: TestClient,
    db_engine: Engine,
    role_name: str,
) -> None:
    headers = _headers_for_role(db_engine, role_name)
    record_id = _seed_billing_record(db_engine)
    vehicle = api_client.post(
        "/api/v1/vehicles",
        json={
            "plate_number": f"蒙S-{role_name}",
            "vehicle_type": "SMALL",
            "allowed_gross_weight_tons": "20.000",
        },
    ).json()

    responses = (
        api_client.get("/api/v1/users", headers=headers),
        api_client.patch(
            f"/api/v1/billing/records/{record_id}/waive",
            headers=headers,
        ),
        api_client.request(
            "DELETE",
            f"/api/v1/vehicles/{vehicle['id']}",
            json={"reason": "security boundary test"},
            headers=headers,
        ),
    )

    for response in responses:
        assert response.status_code == 403
        assert response.json() == {
            "error": {"code": "PERMISSION_DENIED", "message": "Permission denied"}
        }


def test_admin_can_manage_users_waive_and_delete(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    record_id = _seed_billing_record(db_engine)
    vehicle = api_client.post(
        "/api/v1/vehicles",
        json={
            "plate_number": "蒙S-ADMIN",
            "vehicle_type": "SMALL",
            "allowed_gross_weight_tons": "20.000",
        },
    ).json()

    assert api_client.get("/api/v1/users").status_code == 200
    assert api_client.patch(
        f"/api/v1/billing/records/{record_id}/waive"
    ).status_code == 200
    assert api_client.request(
        "DELETE",
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"reason": "security boundary test"},
    ).status_code == 204
