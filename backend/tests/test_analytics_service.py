"""Read-only analytics semantics, including corrected historical overweight events."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import CargoType, WeighingStatus, WeightResult
from app.schemas.vehicle import VehicleCreate
from app.schemas.weighing import (
    GrossWeightInput,
    ReweighInput,
    TareWeightInput,
    WeighingTaskCreate,
)
from app.services.analytics_service import AnalyticsService
from app.services.vehicle_service import VehicleService
from app.services.weighing_service import WeighingService


FIXED_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


def _completed_task(
    session: Session,
    *,
    plate_number: str,
    cargo_type: CargoType,
    final_gross: str,
    completed_at: datetime,
    first_gross: str | None = None,
) -> object:
    vehicle = VehicleService(session).create_vehicle(
        VehicleCreate(
            plate_number=plate_number,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
    )
    service = WeighingService(session)
    task = service.create_task(
        WeighingTaskCreate(vehicle_id=vehicle.id, cargo_type=cargo_type)
    )
    service.record_tare(task.id, TareWeightInput(weight_tons=Decimal("15.820")))
    service.start_loading(task.id)
    service.finish_loading(task.id)
    service.record_gross(
        task.id,
        GrossWeightInput(weight_tons=Decimal(first_gross or final_gross)),
    )
    if first_gross is not None:
        service.record_reweigh(
            task.id,
            ReweighInput(
                weight_tons=Decimal(final_gross),
                remark="卸货后复磅",
            ),
        )
    service.complete_task(task.id)

    task.completed_at = completed_at
    task.gross_time = completed_at
    for record in service.list_records(task.id):
        record.recorded_at = completed_at
    session.commit()
    return task


def _analytics(session: Session) -> AnalyticsService:
    return AnalyticsService(
        session,
        now_provider=lambda: FIXED_NOW,
        business_timezone=timezone.utc,
    )


def test_today_summary_uses_completed_final_weights(db_session: Session) -> None:
    _completed_task(
        db_session,
        plate_number="蒙H10001",
        cargo_type=CargoType.COAL,
        first_gross="50.200",
        final_gross="48.600",
        completed_at=FIXED_NOW,
    )
    _completed_task(
        db_session,
        plate_number="蒙H10002",
        cargo_type=CargoType.TIMBER,
        final_gross="45.820",
        completed_at=FIXED_NOW,
    )

    summary = _analytics(db_session).get_today_weighing_summary()

    assert summary == {
        "date": "2026-09-15",
        "completed_tasks": 2,
        "total_net_weight_tons": "62.780",
        "coal_weight_tons": "32.780",
        "ore_weight_tons": "0.000",
        "timber_weight_tons": "30.000",
        "overweight_events": 1,
    }


def test_cargo_summary_filters_completed_date_range(db_session: Session) -> None:
    _completed_task(
        db_session,
        plate_number="蒙H20001",
        cargo_type=CargoType.COAL,
        final_gross="40.820",
        completed_at=FIXED_NOW,
    )
    _completed_task(
        db_session,
        plate_number="蒙H20002",
        cargo_type=CargoType.COAL,
        final_gross="35.820",
        completed_at=datetime(2026, 9, 14, 12, tzinfo=timezone.utc),
    )

    summary = _analytics(db_session).get_cargo_weight_summary(
        cargo_type=CargoType.COAL,
        start_date=FIXED_NOW.date(),
        end_date=FIXED_NOW.date(),
    )

    assert summary["completed_tasks"] == 1
    assert summary["total_net_weight_tons"] == "25.000"


def test_historical_overweight_survives_final_normal_result(
    db_session: Session,
) -> None:
    task = _completed_task(
        db_session,
        plate_number="蒙H30001",
        cargo_type=CargoType.ORE,
        first_gross="50.200",
        final_gross="48.600",
        completed_at=FIXED_NOW,
    )

    events = _analytics(db_session).get_overweight_records(
        start_date=FIXED_NOW.date(),
        end_date=FIXED_NOW.date(),
    )

    assert task.status is WeighingStatus.COMPLETED
    assert task.weight_result is WeightResult.NORMAL
    assert len(events) == 1
    assert events[0]["first_overweight_weight_tons"] == "50.200"
    assert events[0]["overweight_tons"] == "1.200"
    assert events[0]["final_weight_result"] == "NORMAL"
    assert events[0]["finally_completed"] is True


def test_vehicle_history_returns_recent_task_summary(db_session: Session) -> None:
    task = _completed_task(
        db_session,
        plate_number="蒙H40001",
        cargo_type=CargoType.TIMBER,
        final_gross="42.000",
        completed_at=FIXED_NOW,
    )

    result = _analytics(db_session).get_vehicle_weighing_history(
        plate_number="蒙h40001",
        limit=5,
    )

    assert result["plate_number"] == "蒙H40001"
    assert result["tasks"][0]["task_no"] == task.task_no
    assert result["tasks"][0]["final_net_weight_tons"] == "26.180"


def test_task_detail_contains_ordered_reading_history(db_session: Session) -> None:
    task = _completed_task(
        db_session,
        plate_number="蒙H50001",
        cargo_type=CargoType.COAL,
        first_gross="50.200",
        final_gross="48.600",
        completed_at=FIXED_NOW,
    )

    result = _analytics(db_session).get_weighing_task_detail(task_no=task.task_no)

    assert result["found"] is True
    assert result["plate_number"] == "蒙H50001"
    assert result["net_weight_tons"] == "32.780"
    assert [record["weight_type"] for record in result["records"]] == [
        "TARE",
        "GROSS",
        "REWEIGH",
    ]
