"""Role matrix for billing view, payment confirmation, and waiver."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    CargoType,
    PaymentStatus,
    VehicleType,
    WeighingStatus,
)
from app.models.billing import BillingRecord
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask
from app.security.jwt import create_access_token


def _headers_for_role(engine: Engine, role_name: str) -> dict[str, str]:
    with Session(engine) as session:
        role = session.scalar(select(Role).where(Role.name == role_name))
        assert role is not None
        username = f"billing_{role_name.lower()}"
        user = User(username=username, password_hash="not-used", real_name=username)
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()
        token = create_access_token(user_id=user.id, username=user.username)
    return {"Authorization": f"Bearer {token}"}


def _seed_record(engine: Engine, suffix: str) -> UUID:
    with Session(engine) as session:
        vehicle = Vehicle(
            plate_number=f"蒙C-{suffix}",
            vehicle_type=VehicleType.SMALL,
            allowed_gross_weight_tons=Decimal("20.000"),
        )
        session.add(vehicle)
        session.flush()
        task = WeighingTask(
            task_no=f"PERMISSION-{suffix}",
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


@pytest.mark.parametrize("role_name", ["ADMIN", "OPERATOR", "VIEWER"])
def test_all_builtin_roles_can_view_billing(
    api_client: TestClient,
    db_engine: Engine,
    role_name: str,
) -> None:
    headers = _headers_for_role(db_engine, role_name)

    response = api_client.get("/api/v1/billing/records", headers=headers)

    assert response.status_code == 200


def test_operator_can_pay_but_cannot_waive(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    headers = _headers_for_role(db_engine, "OPERATOR")
    payable = _seed_record(db_engine, "00001")
    waivable = _seed_record(db_engine, "00002")

    paid = api_client.patch(
        f"/api/v1/billing/records/{payable}/pay",
        headers=headers,
    )
    denied = api_client.patch(
        f"/api/v1/billing/records/{waivable}/waive",
        headers=headers,
    )

    assert paid.status_code == 200
    assert denied.status_code == 403


def test_viewer_cannot_change_payment_status(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    headers = _headers_for_role(db_engine, "VIEWER")
    record = _seed_record(db_engine, "00003")

    paid = api_client.patch(
        f"/api/v1/billing/records/{record}/pay",
        headers=headers,
    )
    waived = api_client.patch(
        f"/api/v1/billing/records/{record}/waive",
        headers=headers,
    )

    assert paid.status_code == 403
    assert waived.status_code == 403
