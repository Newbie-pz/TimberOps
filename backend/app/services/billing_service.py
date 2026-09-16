"""Billing generation kept inside the weighing completion transaction."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.domain.enums import PaymentStatus, WeighingStatus
from app.domain.exceptions import BusinessRuleError
from app.models.billing import BillingRecord, BillingRule
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask


class BillingService:
    """Create an idempotent fee snapshot from the rule effective at completion."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_record_for_completed_task(
        self,
        task: WeighingTask,
        *,
        completed_at: datetime | None = None,
    ) -> BillingRecord:
        if task.status is not WeighingStatus.COMPLETED:
            raise BusinessRuleError("billing is only generated for a completed task")

        existing = self._session.scalar(
            select(BillingRecord).where(BillingRecord.weighing_task_id == task.id)
        )
        if existing is not None:
            return existing

        vehicle = self._session.get(Vehicle, task.vehicle_id)
        if vehicle is None:
            raise BusinessRuleError("task vehicle no longer exists")
        if vehicle.vehicle_type is None:
            raise BusinessRuleError(
                "vehicle type must be standardized before completing the task"
            )

        effective_at = completed_at or task.completed_at or utc_now()
        rule = self._session.scalar(
            select(BillingRule)
            .where(
                BillingRule.vehicle_type == vehicle.vehicle_type,
                BillingRule.effective_time <= effective_at,
            )
            .order_by(BillingRule.effective_time.desc(), BillingRule.created_at.desc())
            .limit(1)
        )
        if rule is None:
            raise BusinessRuleError(
                f"no billing rule is effective for vehicle type {vehicle.vehicle_type.value}"
            )

        record = BillingRecord(
            weighing_task=task,
            vehicle_id=vehicle.id,
            vehicle_type_snapshot=vehicle.vehicle_type,
            fee_amount=rule.fee_amount,
            payment_status=PaymentStatus.UNPAID,
        )
        self._session.add(record)
        self._session.flush()
        return record
