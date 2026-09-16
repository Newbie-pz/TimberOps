"""Transactional weighing state-machine tests."""

from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import (
    CargoType,
    WeighingDirection,
    WeighingStatus,
    WeightResult,
    WeightType,
    VehicleType,
)
from app.domain.exceptions import ValidationError
from app.models.audit_log import AuditLog
from app.models.weighing import WeighingRecord, WeighingTask
from app.schemas.vehicle import VehicleCreate
from app.schemas.weighing import (
    CancelWeighingTaskInput,
    GrossWeightInput,
    ReweighInput,
    TareWeightInput,
    WeighingTaskCreate,
)
from app.services.vehicle_service import VehicleService
from app.services.weighing_service import WeighingService


def create_task(db_session: Session) -> tuple[WeighingService, WeighingTask]:
    vehicle = VehicleService(db_session).create_vehicle(
        VehicleCreate(
            plate_number="蒙H12345",
            vehicle_type=VehicleType.LARGE,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
    )
    service = WeighingService(db_session)
    task = service.create_task(
        WeighingTaskCreate(vehicle_id=vehicle.id, cargo_type=CargoType.COAL)
    )
    return service, task


def advance_to_wait_gross(
    db_session: Session,
) -> tuple[WeighingService, WeighingTask]:
    service, task = create_task(db_session)
    service.record_tare(
        task.id,
        TareWeightInput(weight_tons=Decimal("15.820")),
    )
    service.prepare_for_gross(task.id)
    return service, task


def records_for(db_session: Session, task_id: UUID) -> list[WeighingRecord]:
    return list(
        db_session.scalars(
            select(WeighingRecord)
            .where(WeighingRecord.weighing_task_id == task_id)
            .order_by(WeighingRecord.sequence_no)
        )
    )


def test_normal_workflow_completes(db_session: Session) -> None:
    service, task = advance_to_wait_gross(db_session)
    task = service.record_gross(
        task.id,
        GrossWeightInput(weight_tons=Decimal("47.360")),
    )

    assert task.status is WeighingStatus.GROSS_COMPLETED
    assert task.net_weight_tons == Decimal("31.540")
    assert task.overweight_tons == Decimal("0.000")
    assert task.weight_result is WeightResult.NORMAL

    task = service.complete_task(task.id)
    assert task.status is WeighingStatus.COMPLETED
    assert task.completed_at is not None


def test_overweight_cannot_complete_and_waits_for_reweigh(
    db_session: Session,
) -> None:
    service, task = advance_to_wait_gross(db_session)
    task = service.record_gross(
        task.id,
        GrossWeightInput(weight_tons=Decimal("50.200")),
    )

    assert task.status is WeighingStatus.WAIT_GROSS
    assert task.net_weight_tons == Decimal("34.380")
    assert task.overweight_tons == Decimal("1.200")
    assert task.weight_result is WeightResult.OVERWEIGHT
    with pytest.raises(ValidationError):
        service.complete_task(task.id)


def test_invalid_transition_is_rejected(db_session: Session) -> None:
    service, task = create_task(db_session)

    with pytest.raises(ValidationError):
        service.finish_loading(task.id)

    assert task.status is WeighingStatus.WAIT_TARE


def test_tare_moves_directly_to_wait_gross_without_loading(
    db_session: Session,
) -> None:
    service, task = create_task(db_session)
    service.record_tare(task.id, TareWeightInput(weight_tons=Decimal("15.820")))

    task = service.prepare_for_gross(task.id)

    assert task.status is WeighingStatus.WAIT_GROSS
    assert "LOADING" not in {status.value for status in WeighingStatus}


def test_inbound_direction_is_reserved_but_not_supported_in_v1(
    db_session: Session,
) -> None:
    vehicle = VehicleService(db_session).create_vehicle(
        VehicleCreate(
            plate_number="蒙H54321",
            vehicle_type=VehicleType.LARGE,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
    )

    with pytest.raises(ValidationError, match="OUTBOUND"):
        WeighingService(db_session).create_task(
            WeighingTaskCreate(
                vehicle_id=vehicle.id,
                cargo_type=CargoType.ORE,
                weighing_direction=WeighingDirection.INBOUND,
            )
        )


def test_other_cargo_without_name_is_persisted(db_session: Session) -> None:
    vehicle = VehicleService(db_session).create_vehicle(
        VehicleCreate(
            plate_number="蒙H54322",
            vehicle_type=VehicleType.LARGE,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
    )

    task = WeighingService(db_session).create_task(
        WeighingTaskCreate(vehicle_id=vehicle.id, cargo_type=CargoType.OTHER)
    )

    assert task.cargo_type is CargoType.OTHER
    assert task.cargo_name is None


def test_invalid_gross_is_atomic(db_session: Session) -> None:
    service, task = advance_to_wait_gross(db_session)

    with pytest.raises(ValidationError):
        service.record_gross(
            task.id,
            GrossWeightInput(weight_tons=Decimal("15.000")),
        )

    db_session.refresh(task)
    assert task.gross_weight_tons is None
    assert len(records_for(db_session, task.id)) == 1


def test_reweigh_preserves_history_and_updates_current_summary(
    db_session: Session,
) -> None:
    service, task = advance_to_wait_gross(db_session)
    service.record_gross(
        task.id,
        GrossWeightInput(weight_tons=Decimal("50.200")),
    )
    service.record_reweigh(
        task.id,
        ReweighInput(weight_tons=Decimal("49.500"), remark="卸货后第一次复磅"),
    )
    task = service.record_reweigh(
        task.id,
        ReweighInput(weight_tons=Decimal("48.600"), remark="继续卸货后复磅"),
    )

    records = records_for(db_session, task.id)
    assert [record.sequence_no for record in records] == [1, 2, 3, 4]
    assert [record.weight_type for record in records] == [
        WeightType.TARE,
        WeightType.GROSS,
        WeightType.REWEIGH,
        WeightType.REWEIGH,
    ]
    assert [record.weight_tons for record in records] == [
        Decimal("15.820"),
        Decimal("50.200"),
        Decimal("49.500"),
        Decimal("48.600"),
    ]
    assert task.gross_weight_tons == Decimal("48.600")
    assert task.net_weight_tons == Decimal("32.780")
    assert task.overweight_tons == Decimal("0.000")
    assert task.weight_result is WeightResult.NORMAL
    assert task.status is WeighingStatus.GROSS_COMPLETED


def test_completed_task_cannot_be_weighed_again(db_session: Session) -> None:
    service, task = advance_to_wait_gross(db_session)
    service.record_gross(
        task.id,
        GrossWeightInput(weight_tons=Decimal("47.360")),
    )
    service.complete_task(task.id)

    with pytest.raises(ValidationError):
        service.record_reweigh(
            task.id,
            ReweighInput(weight_tons=Decimal("46.000"), remark="非法复磅"),
        )


def test_cancelled_task_cannot_continue_and_reason_is_audited(
    db_session: Session,
) -> None:
    service, task = create_task(db_session)
    task = service.cancel_task(
        task.id,
        CancelWeighingTaskInput(reason="车辆选择错误"),
    )

    assert task.status is WeighingStatus.CANCELLED
    audit = db_session.scalar(select(AuditLog))
    assert audit is not None
    assert audit.reason == "车辆选择错误"
    assert audit.before_value == {"status": "WAIT_TARE"}
    assert audit.after_value == {"status": "CANCELLED"}
    with pytest.raises(ValidationError):
        service.record_tare(
            task.id,
            TareWeightInput(weight_tons=Decimal("15.820")),
        )


def test_completed_task_cannot_be_cancelled(db_session: Session) -> None:
    service, task = advance_to_wait_gross(db_session)
    service.record_gross(
        task.id,
        GrossWeightInput(weight_tons=Decimal("47.360")),
    )
    service.complete_task(task.id)

    with pytest.raises(ValidationError):
        service.cancel_task(
            task.id,
            CancelWeighingTaskInput(reason="不允许的取消"),
        )


def test_service_exposes_no_record_update_or_delete() -> None:
    assert not hasattr(WeighingService, "update_weight_record")
    assert not hasattr(WeighingService, "delete_weight_record")
