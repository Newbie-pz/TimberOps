"""Read-only queries for the append-only audit trail."""

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.exceptions import BusinessRuleError
from app.models.audit_log import AuditLog
from app.models.billing import BillingRecord
from app.models.customer import Customer
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask
from app.schemas.audit import AuditLogRead


UTC_PLUS_8 = timezone(timedelta(hours=8))
TARGET_TYPE_ALIASES = {
    "WeighingTask": "WEIGHING_TASK",
    "WEIGHING_TASK": "WEIGHING_TASK",
    "Vehicle": "VEHICLE",
    "VEHICLE": "VEHICLE",
    "Customer": "CUSTOMER",
    "CUSTOMER": "CUSTOMER",
    "BillingRecord": "BILLING_RECORD",
    "BILLING_RECORD": "BILLING_RECORD",
}


class AuditService:
    """Expose filtered audit history without mutating audit or business data."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_logs(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        operator_id: UUID | None = None,
        action: str | None = None,
        target_type: str | None = None,
    ) -> list[AuditLogRead]:
        """Query audit events with inclusive UTC+8 calendar-date filters."""
        if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
        ):
            raise BusinessRuleError("start_date must be on or before end_date")

        statement = select(AuditLog, User.real_name).outerjoin(
            User,
            User.id == AuditLog.operator_id,
        )
        if start_date is not None:
            statement = statement.where(
                AuditLog.created_at >= self._local_day_start_utc(start_date)
            )
        if end_date is not None:
            statement = statement.where(
                AuditLog.created_at
                < self._local_day_start_utc(end_date + timedelta(days=1))
            )
        if operator_id is not None:
            statement = statement.where(AuditLog.operator_id == operator_id)
        if action is not None:
            statement = statement.where(AuditLog.action == action)
        if target_type is not None:
            statement = statement.where(AuditLog.target_type == target_type)

        rows = self._session.execute(
            statement.order_by(AuditLog.created_at.desc(), AuditLog.id)
        ).all()
        target_displays = self._resolve_target_displays(
            [log for log, _operator_name in rows]
        )
        return [
            AuditLogRead(
                id=log.id,
                operator_id=log.operator_id,
                operator_name=operator_name,
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                target_display=self._target_display(
                    log,
                    target_displays,
                ),
                reason=log.reason,
                before_value=log.before_value,
                after_value=log.after_value,
                created_at=log.created_at,
            )
            for log, operator_name in rows
        ]

    def _resolve_target_displays(
        self,
        logs: list[AuditLog],
    ) -> dict[tuple[str, UUID], str]:
        """Resolve each target type in one query instead of querying per log."""
        ids_by_type: dict[str, set[UUID]] = {}
        for log in logs:
            target_kind = TARGET_TYPE_ALIASES.get(log.target_type)
            if target_kind is not None and log.target_id is not None:
                ids_by_type.setdefault(target_kind, set()).add(log.target_id)

        displays: dict[tuple[str, UUID], str] = {}
        task_ids = ids_by_type.get("WEIGHING_TASK", set())
        if task_ids:
            rows = self._session.execute(
                select(
                    WeighingTask.id,
                    WeighingTask.task_no,
                    Vehicle.plate_number,
                )
                .outerjoin(Vehicle, Vehicle.id == WeighingTask.vehicle_id)
                .where(WeighingTask.id.in_(task_ids))
            )
            for target_id, task_no, plate_number in rows:
                display = self._join_display(task_no, plate_number)
                if display:
                    displays[("WEIGHING_TASK", target_id)] = display

        vehicle_ids = ids_by_type.get("VEHICLE", set())
        if vehicle_ids:
            rows = self._session.execute(
                select(Vehicle.id, Vehicle.plate_number).where(
                    Vehicle.id.in_(vehicle_ids)
                )
            )
            for target_id, plate_number in rows:
                if plate_number:
                    displays[("VEHICLE", target_id)] = plate_number

        customer_ids = ids_by_type.get("CUSTOMER", set())
        if customer_ids:
            rows = self._session.execute(
                select(Customer.id, Customer.name).where(
                    Customer.id.in_(customer_ids)
                )
            )
            for target_id, customer_name in rows:
                if customer_name:
                    displays[("CUSTOMER", target_id)] = customer_name

        billing_ids = ids_by_type.get("BILLING_RECORD", set())
        if billing_ids:
            rows = self._session.execute(
                select(
                    BillingRecord.id,
                    WeighingTask.task_no,
                    Vehicle.plate_number,
                    BillingRecord.fee_amount,
                )
                .outerjoin(
                    WeighingTask,
                    WeighingTask.id == BillingRecord.weighing_task_id,
                )
                .outerjoin(Vehicle, Vehicle.id == BillingRecord.vehicle_id)
                .where(BillingRecord.id.in_(billing_ids))
            )
            for target_id, task_no, plate_number, fee_amount in rows:
                display = self._join_display(
                    task_no,
                    plate_number,
                    f"¥{fee_amount:.2f}" if fee_amount is not None else None,
                )
                if display:
                    displays[("BILLING_RECORD", target_id)] = display
        return displays

    @staticmethod
    def _target_display(
        log: AuditLog,
        displays: dict[tuple[str, UUID], str],
    ) -> str | None:
        if log.target_id is None:
            return None
        target_kind = TARGET_TYPE_ALIASES.get(log.target_type)
        if target_kind is None:
            return str(log.target_id)
        return displays.get((target_kind, log.target_id), str(log.target_id))

    @staticmethod
    def _join_display(*parts: object | None) -> str:
        return " · ".join(str(part) for part in parts if part not in (None, ""))

    @staticmethod
    def _local_day_start_utc(value: date) -> datetime:
        local_start = datetime.combine(value, time.min, tzinfo=UTC_PLUS_8)
        return local_start.astimezone(timezone.utc)
