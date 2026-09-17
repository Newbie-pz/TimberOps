"""Periodic report aggregation rules and UTC+8 boundaries."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.enums import (
    CargoType,
    PaymentStatus,
    VehicleType,
    WeighingDirection,
    WeighingStatus,
    WeightResult,
)
from app.models.billing import BillingRecord
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask
from app.services.report_service import ReportService


def _vehicle(session: Session, plate: str) -> Vehicle:
    vehicle = Vehicle(
        plate_number=plate,
        vehicle_type=VehicleType.MEDIUM,
        allowed_gross_weight_tons=Decimal("49.000"),
    )
    session.add(vehicle)
    session.flush()
    return vehicle


def _task(
    session: Session,
    vehicle: Vehicle,
    *,
    task_no: str,
    created_at: datetime,
    status: WeighingStatus,
    completed_at: datetime | None = None,
    net_weight: Decimal | None = None,
    cargo_type: CargoType = CargoType.COAL,
    fee: Decimal | None = None,
    payment_status: PaymentStatus = PaymentStatus.UNPAID,
    deleted_at: datetime | None = None,
) -> WeighingTask:
    task = WeighingTask(
        task_no=task_no,
        vehicle_id=vehicle.id,
        weighing_direction=WeighingDirection.OUTBOUND,
        cargo_type=cargo_type,
        tare_weight_tons=Decimal("10.000") if net_weight else None,
        gross_weight_tons=(Decimal("10.000") + net_weight) if net_weight else None,
        net_weight_tons=net_weight,
        allowed_gross_weight_tons=Decimal("49.000"),
        overweight_tons=Decimal("0.000"),
        status=status,
        weight_result=(
            WeightResult.NORMAL
            if status is WeighingStatus.COMPLETED
            else WeightResult.PENDING
        ),
        completed_at=completed_at,
        created_at=created_at,
        updated_at=created_at,
        deleted_at=deleted_at,
    )
    session.add(task)
    session.flush()
    if fee is not None:
        session.add(
            BillingRecord(
                weighing_task_id=task.id,
                vehicle_id=vehicle.id,
                vehicle_type_snapshot=VehicleType.MEDIUM,
                fee_amount=fee,
                payment_status=payment_status,
                created_at=completed_at or created_at,
            )
        )
    return task


def test_daily_report_statistics_rankings_and_utc_plus_8_boundary(
    db_session: Session,
) -> None:
    vehicle_a = _vehicle(db_session, "蒙D-RPT01")
    vehicle_b = _vehicle(db_session, "蒙D-RPT02")
    _task(
        db_session,
        vehicle_a,
        task_no="BEFORE-DAY",
        created_at=datetime(2026, 9, 16, 15, 59, tzinfo=timezone.utc),
        status=WeighingStatus.COMPLETED,
        completed_at=datetime(2026, 9, 16, 15, 59, tzinfo=timezone.utc),
        net_weight=Decimal("99.000"),
        fee=Decimal("30.00"),
    )
    _task(
        db_session,
        vehicle_a,
        task_no="TODAY-PAID",
        created_at=datetime(2026, 9, 16, 16, 0, tzinfo=timezone.utc),
        status=WeighingStatus.COMPLETED,
        completed_at=datetime(2026, 9, 16, 16, 1, tzinfo=timezone.utc),
        net_weight=Decimal("12.345"),
        cargo_type=CargoType.TIMBER,
        fee=Decimal("30.00"),
        payment_status=PaymentStatus.PAID,
    )
    _task(
        db_session,
        vehicle_b,
        task_no="TODAY-WAIVED",
        created_at=datetime(2026, 9, 16, 16, 2, tzinfo=timezone.utc),
        status=WeighingStatus.COMPLETED,
        completed_at=datetime(2026, 9, 16, 16, 3, tzinfo=timezone.utc),
        net_weight=Decimal("8.000"),
        cargo_type=CargoType.COAL,
        fee=Decimal("100.00"),
        payment_status=PaymentStatus.WAIVED,
    )
    _task(
        db_session,
        vehicle_b,
        task_no="TODAY-PENDING",
        created_at=datetime(2026, 9, 16, 16, 4, tzinfo=timezone.utc),
        status=WeighingStatus.GROSS_COMPLETED,
        net_weight=Decimal("7.000"),
    )
    _task(
        db_session,
        vehicle_a,
        task_no="TODAY-DELETED",
        created_at=datetime(2026, 9, 16, 16, 5, tzinfo=timezone.utc),
        status=WeighingStatus.COMPLETED,
        completed_at=datetime(2026, 9, 16, 16, 6, tzinfo=timezone.utc),
        net_weight=Decimal("50.000"),
        fee=Decimal("30.00"),
        deleted_at=datetime(2026, 9, 16, 17, 0, tzinfo=timezone.utc),
    )
    db_session.commit()

    report = ReportService(db_session).daily(date(2026, 9, 17))

    assert report.task_count == 3
    assert report.completed_task_count == 2
    assert report.completed_net_weight_tons == Decimal("20.345")
    assert report.income == Decimal("30.00")
    assert [item.cargo_type for item in report.cargo_ranking] == [
        CargoType.TIMBER,
        CargoType.COAL,
    ]
    assert report.vehicle_ranking[0].plate_number == "蒙D-RPT01"
    assert report.vehicle_ranking[0].total_net_weight_tons == Decimal("12.345")


def test_monthly_report_uses_utc_plus_8_month_boundaries(
    db_session: Session,
) -> None:
    vehicle = _vehicle(db_session, "蒙D-RPT03")
    _task(
        db_session,
        vehicle,
        task_no="SEP-START",
        created_at=datetime(2026, 8, 31, 16, 0, tzinfo=timezone.utc),
        status=WeighingStatus.COMPLETED,
        completed_at=datetime(2026, 8, 31, 16, 0, tzinfo=timezone.utc),
        net_weight=Decimal("10.000"),
    )
    _task(
        db_session,
        vehicle,
        task_no="SEP-END",
        created_at=datetime(2026, 9, 30, 15, 59, tzinfo=timezone.utc),
        status=WeighingStatus.COMPLETED,
        completed_at=datetime(2026, 9, 30, 15, 59, tzinfo=timezone.utc),
        net_weight=Decimal("20.000"),
    )
    _task(
        db_session,
        vehicle,
        task_no="OCT-START",
        created_at=datetime(2026, 9, 30, 16, 0, tzinfo=timezone.utc),
        status=WeighingStatus.COMPLETED,
        completed_at=datetime(2026, 9, 30, 16, 0, tzinfo=timezone.utc),
        net_weight=Decimal("40.000"),
    )
    db_session.commit()

    report = ReportService(db_session).monthly(year=2026, month=9)

    assert report.period_start == date(2026, 9, 1)
    assert report.period_end == date(2026, 9, 30)
    assert report.task_count == 2
    assert report.completed_task_count == 2
    assert report.completed_net_weight_tons == Decimal("30.000")


def test_report_empty_period_returns_decimal_zeroes(db_session: Session) -> None:
    report = ReportService(db_session).daily(date(2020, 1, 1))

    assert report.task_count == 0
    assert report.completed_task_count == 0
    assert report.completed_net_weight_tons == Decimal("0.000")
    assert report.income == Decimal("0.00")
    assert report.cargo_ranking == []
    assert report.vehicle_ranking == []
