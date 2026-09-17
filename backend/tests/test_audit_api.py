"""Audit log API filtering, operator resolution, and permission matrix."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.billing import BillingRecord
from app.models.customer import Customer
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask
from app.domain.enums import CargoType, PaymentStatus, VehicleType
from app.security.jwt import create_access_token


def _headers_for_role(engine: Engine, role_name: str) -> dict[str, str]:
    with Session(engine) as session:
        role = session.scalar(select(Role).where(Role.name == role_name))
        assert role is not None
        username = f"audit_{role_name.lower()}"
        user = User(username=username, password_hash="not-used", real_name=username)
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()
        token = create_access_token(user_id=user.id, username=user.username)
    return {"Authorization": f"Bearer {token}"}


def test_audit_logs_return_operator_name_and_support_all_filters(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        operator = User(
            username="audit_operator",
            password_hash="not-used",
            real_name="审计操作员",
        )
        session.add(operator)
        session.flush()
        target_id = uuid4()
        included = AuditLog(
            operator_id=operator.id,
            action="WEIGHING_TASK_COMPLETED",
            target_type="WeighingTask",
            target_id=target_id,
            before_value={"status": "GROSS_COMPLETED"},
            after_value={"status": "COMPLETED"},
            reason=None,
            created_at=datetime(2026, 9, 16, 16, 0, tzinfo=timezone.utc),
        )
        excluded = AuditLog(
            operator_id=operator.id,
            action="BILLING_PAID",
            target_type="BillingRecord",
            target_id=uuid4(),
            before_value={"payment_status": "UNPAID"},
            after_value={"payment_status": "PAID"},
            reason=None,
            created_at=datetime(2026, 9, 16, 15, 59, tzinfo=timezone.utc),
        )
        session.add_all([included, excluded])
        session.commit()
        operator_id = operator.id
        included_id = included.id

    response = api_client.get(
        "/api/v1/audit/logs",
        params={
            "start_date": "2026-09-17",
            "end_date": "2026-09-17",
            "operator_id": str(operator_id),
            "action": "WEIGHING_TASK_COMPLETED",
            "target_type": "WeighingTask",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    item = response.json()[0]
    assert item["id"] == str(included_id)
    assert item["operator_id"] == str(operator_id)
    assert item["operator_name"] == "审计操作员"
    assert item["target_id"] == str(target_id)
    assert item["target_display"] == str(target_id)
    assert item["before_value"] == {"status": "GROSS_COMPLETED"}
    assert item["after_value"] == {"status": "COMPLETED"}


def test_audit_logs_return_empty_list_when_no_data(
    api_client: TestClient,
) -> None:
    response = api_client.get("/api/v1/audit/logs")

    assert response.status_code == 200
    assert response.json() == []


def test_operator_can_view_audit_logs(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    response = api_client.get(
        "/api/v1/audit/logs",
        headers=_headers_for_role(db_engine, "OPERATOR"),
    )

    assert response.status_code == 200


def test_viewer_cannot_view_audit_logs(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    response = api_client.get(
        "/api/v1/audit/logs",
        headers=_headers_for_role(db_engine, "VIEWER"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_audit_logs_resolve_all_business_target_displays(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        vehicle = Vehicle(
            plate_number="蒙H12345",
            vehicle_type=VehicleType.LARGE,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
        customer = Customer(name="XX木材加工厂")
        session.add_all([vehicle, customer])
        session.flush()
        task = WeighingTask(
            task_no="WB202609170012",
            vehicle_id=vehicle.id,
            customer_id=customer.id,
            cargo_type=CargoType.TIMBER,
            allowed_gross_weight_tons=Decimal("49.000"),
            overweight_tons=Decimal("0.000"),
        )
        session.add(task)
        session.flush()
        billing = BillingRecord(
            weighing_task_id=task.id,
            vehicle_id=vehicle.id,
            vehicle_type_snapshot=VehicleType.LARGE,
            fee_amount=Decimal("100.00"),
            payment_status=PaymentStatus.UNPAID,
        )
        session.add(billing)
        session.flush()
        missing_id = uuid4()
        session.add_all(
            [
                AuditLog(
                    action="WEIGHING_TASK_CREATED",
                    target_type="WeighingTask",
                    target_id=task.id,
                    reason=None,
                ),
                AuditLog(
                    action="VEHICLE_DELETED",
                    target_type="Vehicle",
                    target_id=vehicle.id,
                    reason="测试",
                ),
                AuditLog(
                    action="CUSTOMER_DELETED",
                    target_type="Customer",
                    target_id=customer.id,
                    reason="测试",
                ),
                AuditLog(
                    action="BILLING_PAID",
                    target_type="BillingRecord",
                    target_id=billing.id,
                    reason=None,
                ),
                AuditLog(
                    action="WEIGHING_TASK_DELETED",
                    target_type="WEIGHING_TASK",
                    target_id=missing_id,
                    reason="对象已不存在",
                ),
            ]
        )
        session.commit()
        task_id = task.id
        vehicle_id = vehicle.id
        customer_id = customer.id
        billing_id = billing.id

    response = api_client.get("/api/v1/audit/logs")

    assert response.status_code == 200
    displays = {
        (item["target_type"], item["target_id"]): item["target_display"]
        for item in response.json()
    }
    assert displays[("WeighingTask", str(task_id))] == (
        "WB202609170012 · 蒙H12345"
    )
    assert displays[("Vehicle", str(vehicle_id))] == "蒙H12345"
    assert displays[("Customer", str(customer_id))] == "XX木材加工厂"
    assert displays[("BillingRecord", str(billing_id))] == (
        "WB202609170012 · 蒙H12345 · ¥100.00"
    )
    assert displays[("WEIGHING_TASK", str(missing_id))] == str(missing_id)
