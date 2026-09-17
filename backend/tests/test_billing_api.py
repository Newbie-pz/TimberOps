"""Billing record query, transition idempotency, and audit integration."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    CargoType,
    PaymentStatus,
    VehicleType,
    WeighingDirection,
    WeighingStatus,
    WeightResult,
)
from app.models.audit_log import AuditLog
from app.models.billing import BillingRecord
from app.models.customer import Customer
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask


def _seed_record(
    session: Session,
    *,
    suffix: str,
    created_at: datetime,
    payment_status: PaymentStatus = PaymentStatus.UNPAID,
) -> BillingRecord:
    customer = Customer(name=f"客户-{suffix}")
    vehicle = Vehicle(
        plate_number=f"蒙B-{suffix}",
        vehicle_type=VehicleType.MEDIUM,
        allowed_gross_weight_tons=Decimal("49.000"),
    )
    session.add_all([customer, vehicle])
    session.flush()
    task = WeighingTask(
        task_no=f"BILLING-{suffix}",
        vehicle_id=vehicle.id,
        customer_id=customer.id,
        weighing_direction=WeighingDirection.OUTBOUND,
        cargo_type=CargoType.TIMBER,
        tare_weight_tons=Decimal("10.000"),
        gross_weight_tons=Decimal("30.000"),
        net_weight_tons=Decimal("20.000"),
        allowed_gross_weight_tons=Decimal("49.000"),
        overweight_tons=Decimal("0.000"),
        status=WeighingStatus.COMPLETED,
        weight_result=WeightResult.NORMAL,
        completed_at=created_at,
    )
    session.add(task)
    session.flush()
    record = BillingRecord(
        weighing_task_id=task.id,
        vehicle_id=vehicle.id,
        vehicle_type_snapshot=VehicleType.MEDIUM,
        fee_amount=Decimal("30.00"),
        payment_status=payment_status,
        created_at=created_at,
    )
    session.add(record)
    session.commit()
    return record


def test_list_billing_records_supports_all_filters_and_utc_plus_8_dates(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        previous_day = _seed_record(
            session,
            suffix="00001",
            created_at=datetime(2026, 9, 16, 15, 59, tzinfo=timezone.utc),
        )
        current_day = _seed_record(
            session,
            suffix="00002",
            created_at=datetime(2026, 9, 16, 16, 0, tzinfo=timezone.utc),
            payment_status=PaymentStatus.PAID,
        )
        current_id = str(current_day.id)
        current_vehicle_id = str(current_day.vehicle_id)
        current_customer_id = str(current_day.weighing_task.customer_id)
        previous_id = str(previous_day.id)

    response = api_client.get(
        "/api/v1/billing/records",
        params={
            "start_date": "2026-09-17",
            "end_date": "2026-09-17",
            "vehicle_id": current_vehicle_id,
            "customer_id": current_customer_id,
            "payment_status": "PAID",
        },
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [current_id]
    assert response.json()[0]["task_no"] == "BILLING-00002"
    assert response.json()[0]["plate_number"] == "蒙B-00002"
    assert response.json()[0]["customer_name"] == "客户-00002"
    assert previous_id not in {item["id"] for item in response.json()}


def test_pay_is_idempotent_and_writes_one_real_operator_audit(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        record = _seed_record(
            session,
            suffix="00003",
            created_at=datetime.now(timezone.utc),
        )
        record_id = record.id

    first = api_client.patch(
        f"/api/v1/billing/records/{record_id}/pay",
        json={"operator_id": str(uuid4())},
    )
    second = api_client.patch(f"/api/v1/billing/records/{record_id}/pay")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["payment_status"] == "PAID"
    assert first.json()["fee_amount"] == "30.00"
    with Session(db_engine) as session:
        admin = session.scalar(select(User).where(User.username == "test_admin"))
        audits = list(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.target_id == record_id,
                    AuditLog.action == "BILLING_PAID",
                )
            )
        )
        assert admin is not None
        assert len(audits) == 1
        assert audits[0].operator_id == admin.id
        assert audits[0].before_value["payment_status"] == "UNPAID"
        assert audits[0].after_value["payment_status"] == "PAID"


def test_waive_is_idempotent_and_writes_one_audit(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        record = _seed_record(
            session,
            suffix="00004",
            created_at=datetime.now(timezone.utc),
        )
        record_id = record.id

    first = api_client.patch(f"/api/v1/billing/records/{record_id}/waive")
    second = api_client.patch(f"/api/v1/billing/records/{record_id}/waive")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["payment_status"] == "WAIVED"
    with Session(db_engine) as session:
        assert session.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.target_id == record_id,
                AuditLog.action == "BILLING_WAIVED",
            )
        ) == 1


def test_paid_record_cannot_be_waived(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        record = _seed_record(
            session,
            suffix="00005",
            created_at=datetime.now(timezone.utc),
            payment_status=PaymentStatus.PAID,
        )
        record_id = record.id

    response = api_client.patch(f"/api/v1/billing/records/{record_id}/waive")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_CONFLICT"
