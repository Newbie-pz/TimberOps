"""Billing rules and completion-time charge generation."""

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import CargoType, PaymentStatus, VehicleType
from app.models.billing import BillingRecord
from app.schemas.vehicle import VehicleCreate
from app.schemas.weighing import GrossWeightInput, ReweighInput, TareWeightInput, WeighingTaskCreate
from app.services.billing_service import BillingService
from app.services.vehicle_service import VehicleService
from app.services.weighing_service import WeighingService


def _task(session: Session, vehicle_type: VehicleType) -> object:
    vehicle = VehicleService(session).create_vehicle(
        VehicleCreate(
            plate_number=f"TEST-{vehicle_type.value}",
            vehicle_type=vehicle_type,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
    )
    return WeighingService(session).create_task(
        WeighingTaskCreate(vehicle_id=vehicle.id, cargo_type=CargoType.ORE)
    )


def _advance_to_gross(session: Session, vehicle_type: VehicleType) -> tuple[WeighingService, object]:
    task = _task(session, vehicle_type)
    service = WeighingService(session)
    service.record_tare(task.id, TareWeightInput(weight_tons=Decimal("10.000")))
    service.prepare_for_gross(task.id)
    return service, task


@pytest.mark.parametrize(
    ("vehicle_type", "expected_fee"),
    [
        (VehicleType.SMALL, Decimal("10.00")),
        (VehicleType.MEDIUM, Decimal("30.00")),
        (VehicleType.LARGE, Decimal("100.00")),
    ],
)
def test_vehicle_types_generate_configured_fee(
    db_session: Session,
    vehicle_type: VehicleType,
    expected_fee: Decimal,
) -> None:
    service, task = _advance_to_gross(db_session, vehicle_type)
    service.record_gross(task.id, GrossWeightInput(weight_tons=Decimal("40.000")))

    service.complete_task(task.id)

    record = db_session.scalar(
        select(BillingRecord).where(BillingRecord.weighing_task_id == task.id)
    )
    assert record is not None
    assert record.fee_amount == expected_fee
    assert record.vehicle_type_snapshot is vehicle_type
    assert record.payment_status is PaymentStatus.UNPAID


def test_unfinished_task_does_not_generate_fee(db_session: Session) -> None:
    task = _task(db_session, VehicleType.SMALL)

    count = db_session.scalar(select(func.count(BillingRecord.id)))

    assert task.billing_record is None
    assert count == 0


def test_overweight_reweigh_generates_one_fee_only_after_completion(
    db_session: Session,
) -> None:
    service, task = _advance_to_gross(db_session, VehicleType.MEDIUM)
    service.record_gross(task.id, GrossWeightInput(weight_tons=Decimal("50.000")))
    assert db_session.scalar(select(func.count(BillingRecord.id))) == 0

    service.record_reweigh(
        task.id,
        ReweighInput(weight_tons=Decimal("48.000"), remark="卸货复磅"),
    )
    service.complete_task(task.id)

    assert db_session.scalar(select(func.count(BillingRecord.id))) == 1


def test_billing_record_generation_is_idempotent(db_session: Session) -> None:
    service, task = _advance_to_gross(db_session, VehicleType.LARGE)
    service.record_gross(task.id, GrossWeightInput(weight_tons=Decimal("40.000")))
    service.complete_task(task.id)

    first = BillingService(db_session).ensure_record_for_completed_task(task)
    second = BillingService(db_session).ensure_record_for_completed_task(task)

    assert first.id == second.id
    assert db_session.scalar(select(func.count(BillingRecord.id))) == 1


def test_vehicle_type_enum_rejects_invalid_input() -> None:
    with pytest.raises(PydanticValidationError):
        VehicleCreate(
            plate_number="蒙H79999",
            vehicle_type="重型货车",
            allowed_gross_weight_tons=Decimal("49.000"),
        )
