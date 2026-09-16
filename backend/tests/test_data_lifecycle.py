"""Soft-deletion rules and audit coverage."""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import CargoType, VehicleType
from app.domain.exceptions import (
    CustomerHasHistoryError,
    InvalidStateError,
    VehicleHasHistoryError,
)
from app.models.audit_log import AuditLog
from app.schemas.customer import CustomerCreate
from app.schemas.lifecycle import DeleteEntityInput
from app.schemas.vehicle import VehicleCreate
from app.schemas.weighing import GrossWeightInput, TareWeightInput, WeighingTaskCreate
from app.services.customer_service import CustomerService
from app.services.vehicle_service import VehicleService
from app.services.weighing_service import WeighingService


def _vehicle(session: Session, plate: str = "蒙H70001") -> object:
    return VehicleService(session).create_vehicle(
        VehicleCreate(
            plate_number=plate,
            vehicle_type=VehicleType.MEDIUM,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
    )


def _task(session: Session, *, customer_id: object | None = None) -> object:
    vehicle = _vehicle(session)
    return WeighingService(session).create_task(
        WeighingTaskCreate(
            vehicle_id=vehicle.id,
            customer_id=customer_id,
            cargo_type=CargoType.TIMBER,
        )
    )


def test_delete_vehicle_without_history_soft_deletes_and_audits(
    db_session: Session,
) -> None:
    vehicle = _vehicle(db_session)
    operator_id = uuid4()

    VehicleService(db_session).delete_vehicle(
        vehicle.id,
        DeleteEntityInput(reason="重复档案"),
        operator_id=operator_id,
    )

    assert vehicle.deleted_at is not None
    assert VehicleService(db_session).list_vehicles() == []
    audit = db_session.scalar(select(AuditLog))
    assert audit is not None
    assert audit.action == "VEHICLE_DELETED"
    assert audit.operator_id == operator_id
    assert audit.reason == "重复档案"


def test_delete_vehicle_with_history_is_rejected(db_session: Session) -> None:
    task = _task(db_session)

    with pytest.raises(VehicleHasHistoryError):
        VehicleService(db_session).delete_vehicle(
            task.vehicle_id,
            DeleteEntityInput(reason="尝试删除"),
        )


def test_delete_customer_with_history_is_rejected(db_session: Session) -> None:
    customer = CustomerService(db_session).create_customer(
        CustomerCreate(name="历史客户")
    )
    _task(db_session, customer_id=customer.id)

    with pytest.raises(CustomerHasHistoryError):
        CustomerService(db_session).delete_customer(
            customer.id,
            DeleteEntityInput(reason="尝试删除"),
        )


def test_delete_completed_task_is_rejected(db_session: Session) -> None:
    task = _task(db_session)
    service = WeighingService(db_session)
    service.record_tare(task.id, TareWeightInput(weight_tons=Decimal("15.000")))
    service.prepare_for_gross(task.id)
    service.record_gross(task.id, GrossWeightInput(weight_tons=Decimal("45.000")))
    service.complete_task(task.id)

    with pytest.raises(InvalidStateError):
        service.delete_task(task.id, DeleteEntityInput(reason="不应允许"))


def test_delete_unfinished_task_soft_deletes_and_audits(
    db_session: Session,
) -> None:
    task = _task(db_session)
    operator_id = uuid4()

    WeighingService(db_session).delete_task(
        task.id,
        DeleteEntityInput(reason="录入车辆错误"),
        operator_id=operator_id,
    )

    assert task.deleted_at is not None
    assert task.deleted_by == operator_id
    assert task.delete_reason == "录入车辆错误"
    assert WeighingService(db_session).list_tasks() == []
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "WEIGHING_TASK_DELETED")
    )
    assert audit is not None
    assert audit.reason == "录入车辆错误"


def test_history_protection_error_code_is_public(api_client: object) -> None:
    vehicle_response = api_client.post(
        "/api/v1/vehicles",
        json={
            "plate_number": "蒙H70002",
            "vehicle_type": "SMALL",
            "allowed_gross_weight_tons": "10.000",
        },
    )
    vehicle_id = vehicle_response.json()["id"]
    api_client.post(
        "/api/v1/weighing/tasks",
        json={"vehicle_id": vehicle_id, "cargo_type": "COAL"},
    )

    response = api_client.request(
        "DELETE",
        f"/api/v1/vehicles/{vehicle_id}",
        json={"reason": "测试"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "VEHICLE_HAS_HISTORY",
            "message": "该车辆存在历史称重记录，无法删除",
        }
    }
