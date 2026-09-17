"""Read-only aggregation service for the operations dashboard."""

from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.domain.enums import CargoType, PaymentStatus, WeighingStatus
from app.models.billing import BillingRecord
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask
from app.schemas.dashboard import (
    CargoWeightRankingItem,
    DashboardOverview,
    StatusDistributionItem,
    VehicleTransportRankingItem,
)


UTC_PLUS_8 = timezone(timedelta(hours=8))
WEIGHT_ZERO = Decimal("0.000")
MONEY_ZERO = Decimal("0.00")


class DashboardService:
    """Aggregate operational facts without changing domain state."""

    def __init__(
        self,
        session: Session,
        *,
        now_factory: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session = session
        self._now_factory = now_factory

    def get_overview(self) -> DashboardOverview:
        """Return the current UTC+8 business-day and lifetime rankings."""
        business_date, start_utc, end_utc = self._business_day_bounds(
            self._now_factory()
        )
        active_task = WeighingTask.deleted_at.is_(None)
        completed_today = (
            active_task,
            WeighingTask.status == WeighingStatus.COMPLETED,
            WeighingTask.completed_at >= start_utc,
            WeighingTask.completed_at < end_utc,
        )

        today_task_count = self._session.scalar(
            select(func.count(WeighingTask.id)).where(
                active_task,
                WeighingTask.created_at >= start_utc,
                WeighingTask.created_at < end_utc,
            )
        ) or 0
        today_completed_task_count = self._session.scalar(
            select(func.count(WeighingTask.id)).where(*completed_today)
        ) or 0
        pending_task_count = self._session.scalar(
            select(func.count(WeighingTask.id)).where(
                active_task,
                WeighingTask.status.not_in(
                    (WeighingStatus.COMPLETED, WeighingStatus.CANCELLED)
                ),
            )
        ) or 0
        today_completed_net_weight = self._decimal_or(
            self._session.scalar(
                select(func.sum(WeighingTask.net_weight_tons)).where(
                    *completed_today
                )
            ),
            WEIGHT_ZERO,
        )
        today_income = self._decimal_or(
            self._session.scalar(
                select(func.sum(BillingRecord.fee_amount))
                .join(
                    WeighingTask,
                    WeighingTask.id == BillingRecord.weighing_task_id,
                )
                .where(
                    *completed_today,
                    BillingRecord.payment_status != PaymentStatus.WAIVED,
                )
            ),
            MONEY_ZERO,
        )

        return DashboardOverview(
            business_date=business_date,
            today_task_count=int(today_task_count),
            today_completed_task_count=int(today_completed_task_count),
            pending_task_count=int(pending_task_count),
            today_completed_net_weight_tons=today_completed_net_weight.quantize(
                Decimal("0.001")
            ),
            today_income=today_income.quantize(Decimal("0.01")),
            status_distribution=self._status_distribution(),
            cargo_weight_ranking=self._cargo_weight_ranking(completed_today),
            vehicle_transport_ranking=self._vehicle_transport_ranking(),
        )

    def _status_distribution(self) -> list[StatusDistributionItem]:
        rows = self._session.execute(
            select(WeighingTask.status, func.count(WeighingTask.id))
            .where(WeighingTask.deleted_at.is_(None))
            .group_by(WeighingTask.status)
        ).all()
        counts = {WeighingStatus(status): int(count) for status, count in rows}
        return [
            StatusDistributionItem(status=status, count=counts.get(status, 0))
            for status in WeighingStatus
        ]

    def _cargo_weight_ranking(
        self,
        completed_today: tuple[object, ...],
    ) -> list[CargoWeightRankingItem]:
        total_weight = func.sum(WeighingTask.net_weight_tons)
        rows = self._session.execute(
            select(
                WeighingTask.cargo_type,
                func.count(WeighingTask.id),
                total_weight,
            )
            .where(*completed_today)
            .group_by(WeighingTask.cargo_type)
            .order_by(total_weight.desc(), WeighingTask.cargo_type.asc())
        ).all()
        return [
            CargoWeightRankingItem(
                cargo_type=CargoType(cargo_type),
                completed_task_count=int(task_count),
                total_net_weight_tons=self._decimal_or(
                    weight,
                    WEIGHT_ZERO,
                ).quantize(Decimal("0.001")),
            )
            for cargo_type, task_count, weight in rows
        ]

    def _vehicle_transport_ranking(self) -> list[VehicleTransportRankingItem]:
        total_weight = func.sum(WeighingTask.net_weight_tons)
        completed_count = func.count(WeighingTask.id)
        rows = self._session.execute(
            select(
                Vehicle.id,
                Vehicle.plate_number,
                completed_count,
                total_weight,
            )
            .join(WeighingTask, WeighingTask.vehicle_id == Vehicle.id)
            .where(
                WeighingTask.deleted_at.is_(None),
                WeighingTask.status == WeighingStatus.COMPLETED,
            )
            .group_by(Vehicle.id, Vehicle.plate_number)
            .order_by(
                total_weight.desc(),
                completed_count.desc(),
                Vehicle.plate_number.asc(),
            )
            .limit(10)
        ).all()
        return [
            VehicleTransportRankingItem(
                vehicle_id=vehicle_id,
                plate_number=plate_number,
                completed_task_count=int(task_count),
                total_net_weight_tons=self._decimal_or(
                    weight,
                    WEIGHT_ZERO,
                ).quantize(Decimal("0.001")),
            )
            for vehicle_id, plate_number, task_count, weight in rows
        ]

    @staticmethod
    def _business_day_bounds(now: datetime) -> tuple[date, datetime, datetime]:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Dashboard clock must return a timezone-aware datetime")
        local_date = now.astimezone(UTC_PLUS_8).date()
        start_local = datetime.combine(local_date, time.min, tzinfo=UTC_PLUS_8)
        end_local = start_local + timedelta(days=1)
        return (
            local_date,
            start_local.astimezone(timezone.utc),
            end_local.astimezone(timezone.utc),
        )

    @staticmethod
    def _decimal_or(value: Decimal | int | None, default: Decimal) -> Decimal:
        if value is None:
            return default
        return value if isinstance(value, Decimal) else Decimal(value)
