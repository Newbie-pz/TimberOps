"""Dashboard aggregation rules and UTC+8 business-day boundaries."""

from datetime import datetime, timezone
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
from app.services.dashboard_service import DashboardService


FIXED_NOW = datetime(2026, 9, 16, 16, 30, tzinfo=timezone.utc)


def _vehicle(session: Session, plate_number: str) -> Vehicle:
    vehicle = Vehicle(
        plate_number=plate_number,
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
    cargo_type: CargoType = CargoType.COAL,
    completed_at: datetime | None = None,
    net_weight: Decimal | None = None,
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
    )
    session.add(task)
    session.flush()
    return task


def _overview(session: Session):
    return DashboardService(
        session,
        now_factory=lambda: FIXED_NOW,
    ).get_overview()


def test_dashboard_uses_utc_plus_8_day_and_only_completed_weight(
    db_session: Session,
) -> None:
    vehicle = _vehicle(db_session, "蒙A-DASH01")
    # UTC+8 day starts at 2026-09-16 16:00 UTC.
    _task(
        db_session,
        vehicle,
        task_no="PREVIOUS-DAY",
        created_at=datetime(2026, 9, 16, 15, 59, tzinfo=timezone.utc),
        status=WeighingStatus.COMPLETED,
        completed_at=datetime(2026, 9, 16, 15, 59, tzinfo=timezone.utc),
        net_weight=Decimal("99.000"),
    )
    _task(
        db_session,
        vehicle,
        task_no="TODAY-COMPLETE",
        created_at=datetime(2026, 9, 16, 16, 0, tzinfo=timezone.utc),
        status=WeighingStatus.COMPLETED,
        completed_at=datetime(2026, 9, 16, 16, 1, tzinfo=timezone.utc),
        net_weight=Decimal("12.345"),
    )
    _task(
        db_session,
        vehicle,
        task_no="TODAY-PENDING",
        created_at=datetime(2026, 9, 16, 16, 2, tzinfo=timezone.utc),
        status=WeighingStatus.GROSS_COMPLETED,
        net_weight=Decimal("8.000"),
    )
    db_session.commit()

    overview = _overview(db_session)

    assert overview.business_date.isoformat() == "2026-09-17"
    assert overview.timezone == "UTC+08:00"
    assert overview.today_task_count == 2
    assert overview.today_completed_task_count == 1
    assert overview.pending_task_count == 1
    assert overview.today_completed_net_weight_tons == Decimal("12.345")
    assert overview.cargo_weight_ranking[0].total_net_weight_tons == Decimal(
        "12.345"
    )


def test_dashboard_income_excludes_waived_but_includes_open_charges(
    db_session: Session,
) -> None:
    vehicle = _vehicle(db_session, "蒙A-DASH02")
    for index, (status, fee) in enumerate(
        (
            (PaymentStatus.PAID, Decimal("10.00")),
            (PaymentStatus.UNPAID, Decimal("30.00")),
            (PaymentStatus.WAIVED, Decimal("100.00")),
        ),
        start=1,
    ):
        task = _task(
            db_session,
            vehicle,
            task_no=f"BILL-{index}",
            created_at=datetime(2026, 9, 16, 16, index, tzinfo=timezone.utc),
            status=WeighingStatus.COMPLETED,
            completed_at=datetime(2026, 9, 16, 16, index, tzinfo=timezone.utc),
            net_weight=Decimal(f"{index}.000"),
        )
        db_session.add(
            BillingRecord(
                weighing_task_id=task.id,
                vehicle_id=vehicle.id,
                vehicle_type_snapshot=VehicleType.MEDIUM,
                fee_amount=fee,
                payment_status=status,
            )
        )
    db_session.commit()

    overview = _overview(db_session)

    assert overview.today_income == Decimal("40.00")
    assert overview.currency == "CNY"


def test_dashboard_empty_data_has_decimal_zeroes_and_stable_statuses(
    db_session: Session,
) -> None:
    overview = _overview(db_session)

    assert overview.today_task_count == 0
    assert overview.today_completed_task_count == 0
    assert overview.pending_task_count == 0
    assert overview.today_completed_net_weight_tons == Decimal("0.000")
    assert overview.today_income == Decimal("0.00")
    assert overview.cargo_weight_ranking == []
    assert overview.vehicle_transport_ranking == []
    assert {item.status for item in overview.status_distribution} == set(
        WeighingStatus
    )
    assert all(item.count == 0 for item in overview.status_distribution)


def test_vehicle_ranking_is_limited_and_orders_completed_weight(
    db_session: Session,
) -> None:
    for index in range(12):
        vehicle = _vehicle(db_session, f"蒙A-{index:05d}")
        _task(
            db_session,
            vehicle,
            task_no=f"RANK-{index}",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            status=WeighingStatus.COMPLETED,
            completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            net_weight=Decimal(f"{index + 1}.000"),
        )
    db_session.commit()

    ranking = _overview(db_session).vehicle_transport_ranking

    assert len(ranking) == 10
    assert ranking[0].plate_number == "蒙A-00011"
    assert ranking[0].total_net_weight_tons == Decimal("12.000")
    assert ranking[-1].total_net_weight_tons == Decimal("3.000")
