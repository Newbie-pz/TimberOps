"""Deterministic, read-only queries shared by AI tools and future dashboards."""

from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.domain.enums import CargoType, WeighingStatus, WeightType
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingRecord, WeighingTask


TON_QUANTUM = Decimal("0.001")


def _tons(value: Decimal | None) -> str:
    """Serialize database NUMERIC values without ever converting through float."""
    normalized = (value or Decimal("0")).quantize(
        TON_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
    return format(normalized, "f")


def _timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class AnalyticsService:
    """Expose an intentionally small allow-list of read-only business queries."""

    def __init__(
        self,
        session: Session,
        *,
        now_provider: Callable[[], datetime] = utc_now,
        business_timezone: tzinfo = timezone(timedelta(hours=8)),
    ) -> None:
        self._session = session
        self._now_provider = now_provider
        self._business_timezone = business_timezone

    def get_today_weighing_summary(self) -> dict[str, Any]:
        """Summarize final completed weights and historical overweight events today."""
        today = self._now_provider().astimezone(self._business_timezone).date()
        tasks = self._completed_tasks(start_date=today, end_date=today)
        cargo_totals = {cargo_type: Decimal("0") for cargo_type in CargoType}
        total = Decimal("0")
        for task in tasks:
            net_weight = task.net_weight_tons or Decimal("0")
            total += net_weight
            cargo_totals[task.cargo_type] += net_weight

        overweight_events = self.get_overweight_records(
            start_date=today,
            end_date=today,
        )
        return {
            "date": today.isoformat(),
            "completed_tasks": len(tasks),
            "total_net_weight_tons": _tons(total),
            "coal_weight_tons": _tons(cargo_totals[CargoType.COAL]),
            "ore_weight_tons": _tons(cargo_totals[CargoType.ORE]),
            "timber_weight_tons": _tons(cargo_totals[CargoType.TIMBER]),
            "overweight_events": len(overweight_events),
        }

    def get_cargo_weight_summary(
        self,
        *,
        cargo_type: CargoType,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Return final net weight for completed tasks of one cargo category."""
        tasks = [
            task
            for task in self._completed_tasks(
                start_date=start_date,
                end_date=end_date,
                cargo_type=cargo_type,
            )
        ]
        total = sum(
            (task.net_weight_tons or Decimal("0") for task in tasks),
            start=Decimal("0"),
        )
        return {
            "cargo_type": cargo_type.value,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "completed_tasks": len(tasks),
            "total_net_weight_tons": _tons(total),
        }

    def get_overweight_records(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Return each task's first historical reading above its weight snapshot.

        The current task result is deliberately not used to identify the event: a
        successful REWEIGH changes it back to NORMAL but never removes the earlier
        immutable overweight reading.
        """
        start_at, end_before = self._date_bounds(start_date, end_date)
        first_event = (
            select(
                WeighingRecord.weighing_task_id.label("task_id"),
                func.min(WeighingRecord.sequence_no).label("sequence_no"),
            )
            .join(
                WeighingTask,
                WeighingTask.id == WeighingRecord.weighing_task_id,
            )
            .where(
                WeighingRecord.weight_type.in_(
                    (WeightType.GROSS, WeightType.REWEIGH)
                ),
                WeighingRecord.weight_tons
                > WeighingTask.allowed_gross_weight_tons,
            )
            .group_by(WeighingRecord.weighing_task_id)
            .subquery()
        )
        statement = (
            select(WeighingTask, WeighingRecord, Vehicle.plate_number)
            .join(
                WeighingRecord,
                WeighingRecord.weighing_task_id == WeighingTask.id,
            )
            .join(
                first_event,
                and_(
                    first_event.c.task_id == WeighingRecord.weighing_task_id,
                    first_event.c.sequence_no == WeighingRecord.sequence_no,
                ),
            )
            .join(Vehicle, Vehicle.id == WeighingTask.vehicle_id)
            .order_by(
                WeighingRecord.recorded_at,
                WeighingTask.id,
            )
        )
        statement = self._filter_datetime(
            statement,
            WeighingRecord.recorded_at,
            start_at,
            end_before,
        )

        results: list[dict[str, Any]] = []
        for task, record, plate_number in self._session.execute(statement):
            results.append(
                {
                    "plate_number": plate_number,
                    "task_no": task.task_no,
                    "cargo_type": task.cargo_type.value,
                    "first_overweight_weight_tons": _tons(record.weight_tons),
                    "allowed_gross_weight_tons": _tons(
                        task.allowed_gross_weight_tons
                    ),
                    "overweight_tons": _tons(
                        record.weight_tons - task.allowed_gross_weight_tons
                    ),
                    "event_time": _timestamp(record.recorded_at),
                    "final_status": task.status.value,
                    "final_weight_result": task.weight_result.value,
                    "finally_completed": task.status is WeighingStatus.COMPLETED,
                }
            )
        return results

    def get_vehicle_weighing_history(
        self,
        *,
        plate_number: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Return recent tasks for an exact, case-insensitive plate number."""
        normalized_plate = plate_number.strip().upper()
        if not normalized_plate:
            raise ValueError("plate_number must not be blank")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        vehicle = self._session.scalar(
            select(Vehicle).where(
                func.upper(Vehicle.plate_number) == normalized_plate
            )
        )
        if vehicle is None:
            return {"plate_number": normalized_plate, "tasks": []}

        event_time = func.coalesce(
            WeighingTask.completed_at,
            WeighingTask.gross_time,
            WeighingTask.created_at,
        )
        tasks = list(
            self._session.scalars(
                select(WeighingTask)
                .where(WeighingTask.vehicle_id == vehicle.id)
                .order_by(event_time.desc(), WeighingTask.id.desc())
                .limit(limit)
            )
        )
        return {
            "plate_number": vehicle.plate_number,
            "tasks": [
                {
                    "task_no": task.task_no,
                    "cargo_type": task.cargo_type.value,
                    "final_net_weight_tons": (
                        _tons(task.net_weight_tons)
                        if task.net_weight_tons is not None
                        else None
                    ),
                    "status": task.status.value,
                    "weight_result": task.weight_result.value,
                    "time": _timestamp(
                        task.completed_at or task.gross_time or task.created_at
                    ),
                }
                for task in tasks
            ],
        }

    def get_weighing_task_detail(self, *, task_no: str) -> dict[str, Any]:
        """Return one task business summary and its append-only reading history."""
        normalized_task_no = task_no.strip().upper()
        if not normalized_task_no:
            raise ValueError("task_no must not be blank")
        task = self._session.scalar(
            select(WeighingTask).where(
                func.upper(WeighingTask.task_no) == normalized_task_no
            )
        )
        if task is None:
            return {"task_no": normalized_task_no, "found": False}

        vehicle = self._session.get(Vehicle, task.vehicle_id)
        customer = (
            self._session.get(Customer, task.customer_id)
            if task.customer_id is not None
            else None
        )
        records = list(
            self._session.scalars(
                select(WeighingRecord)
                .where(WeighingRecord.weighing_task_id == task.id)
                .order_by(WeighingRecord.sequence_no)
            )
        )
        return {
            "found": True,
            "task_no": task.task_no,
            "plate_number": vehicle.plate_number if vehicle else None,
            "customer_name": customer.name if customer else None,
            "cargo_type": task.cargo_type.value,
            "cargo_name": task.cargo_name,
            "cargo_remark": task.cargo_remark,
            "driver_name": task.driver_name_snapshot,
            "tare_weight_tons": (
                _tons(task.tare_weight_tons)
                if task.tare_weight_tons is not None
                else None
            ),
            "gross_weight_tons": (
                _tons(task.gross_weight_tons)
                if task.gross_weight_tons is not None
                else None
            ),
            "net_weight_tons": (
                _tons(task.net_weight_tons)
                if task.net_weight_tons is not None
                else None
            ),
            "allowed_gross_weight_tons": _tons(
                task.allowed_gross_weight_tons
            ),
            "overweight_tons": _tons(task.overweight_tons),
            "status": task.status.value,
            "weight_result": task.weight_result.value,
            "created_at": _timestamp(task.created_at),
            "completed_at": _timestamp(task.completed_at),
            "records": [
                {
                    "sequence_no": record.sequence_no,
                    "weight_type": record.weight_type.value,
                    "weight_tons": _tons(record.weight_tons),
                    "recorded_at": _timestamp(record.recorded_at),
                    "source": record.source.value,
                    "remark": record.remark,
                }
                for record in records
            ],
        }

    def _completed_tasks(
        self,
        *,
        start_date: date | None,
        end_date: date | None,
        cargo_type: CargoType | None = None,
    ) -> list[WeighingTask]:
        start_at, end_before = self._date_bounds(start_date, end_date)
        statement = select(WeighingTask).where(
            WeighingTask.status == WeighingStatus.COMPLETED,
            WeighingTask.completed_at.is_not(None),
        )
        if cargo_type is not None:
            statement = statement.where(WeighingTask.cargo_type == cargo_type)
        statement = self._filter_datetime(
            statement,
            WeighingTask.completed_at,
            start_at,
            end_before,
        )
        return list(self._session.scalars(statement))

    def _date_bounds(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[datetime | None, datetime | None]:
        if start_date and end_date and start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        start_at = (
            datetime.combine(start_date, time.min, self._business_timezone)
            .astimezone(timezone.utc)
            if start_date
            else None
        )
        end_before = (
            datetime.combine(
                end_date + timedelta(days=1),
                time.min,
                self._business_timezone,
            ).astimezone(timezone.utc)
            if end_date
            else None
        )
        return start_at, end_before

    @staticmethod
    def _filter_datetime(
        statement: Select[Any],
        column: Any,
        start_at: datetime | None,
        end_before: datetime | None,
    ) -> Select[Any]:
        if start_at is not None:
            statement = statement.where(column >= start_at)
        if end_before is not None:
            statement = statement.where(column < end_before)
        return statement
