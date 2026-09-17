"""Billing generation and audited payment-state management."""

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.domain.enums import PaymentStatus, WeighingStatus
from app.domain.exceptions import BusinessRuleError, NotFoundError
from app.models.audit_log import AuditLog
from app.models.billing import BillingRecord, BillingRule
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask
from app.schemas.billing import BillingRecordListItem


UTC_PLUS_8 = timezone(timedelta(hours=8))


class BillingService:
    """Create fee snapshots and manage their limited payment lifecycle."""

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

    def list_records(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        vehicle_id: UUID | None = None,
        customer_id: UUID | None = None,
        payment_status: PaymentStatus | None = None,
    ) -> list[BillingRecordListItem]:
        """List fee snapshots using inclusive UTC+8 calendar-date filters."""
        if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
        ):
            raise BusinessRuleError("start_date must be on or before end_date")

        statement = (
            select(
                BillingRecord,
                WeighingTask.task_no,
                Vehicle.plate_number,
                WeighingTask.customer_id,
                Customer.name,
                WeighingTask.completed_at,
            )
            .join(WeighingTask, WeighingTask.id == BillingRecord.weighing_task_id)
            .join(Vehicle, Vehicle.id == BillingRecord.vehicle_id)
            .outerjoin(Customer, Customer.id == WeighingTask.customer_id)
            .where(WeighingTask.deleted_at.is_(None))
        )
        if start_date is not None:
            statement = statement.where(
                BillingRecord.created_at >= self._local_day_start_utc(start_date)
            )
        if end_date is not None:
            statement = statement.where(
                BillingRecord.created_at
                < self._local_day_start_utc(end_date + timedelta(days=1))
            )
        if vehicle_id is not None:
            statement = statement.where(BillingRecord.vehicle_id == vehicle_id)
        if customer_id is not None:
            statement = statement.where(WeighingTask.customer_id == customer_id)
        if payment_status is not None:
            statement = statement.where(
                BillingRecord.payment_status == payment_status
            )

        rows = self._session.execute(
            statement.order_by(BillingRecord.created_at.desc(), BillingRecord.id)
        ).all()
        return [
            BillingRecordListItem(
                id=record.id,
                weighing_task_id=record.weighing_task_id,
                vehicle_id=record.vehicle_id,
                vehicle_type_snapshot=record.vehicle_type_snapshot,
                fee_amount=record.fee_amount,
                payment_status=record.payment_status,
                created_at=record.created_at,
                task_no=task_no,
                plate_number=plate_number,
                customer_id=record_customer_id,
                customer_name=customer_name,
                completed_at=completed_at,
            )
            for (
                record,
                task_no,
                plate_number,
                record_customer_id,
                customer_name,
                completed_at,
            ) in rows
        ]

    def mark_paid(self, record_id: UUID, *, operator_id: UUID) -> BillingRecord:
        """Idempotently transition an unpaid fee to paid with one audit event."""
        return self._transition_payment_status(
            record_id,
            target=PaymentStatus.PAID,
            action="BILLING_PAID",
            operator_id=operator_id,
        )

    def waive(self, record_id: UUID, *, operator_id: UUID) -> BillingRecord:
        """Idempotently transition an unpaid fee to waived with one audit event."""
        return self._transition_payment_status(
            record_id,
            target=PaymentStatus.WAIVED,
            action="BILLING_WAIVED",
            operator_id=operator_id,
        )

    def _transition_payment_status(
        self,
        record_id: UUID,
        *,
        target: PaymentStatus,
        action: str,
        operator_id: UUID,
    ) -> BillingRecord:
        record = self._session.scalar(
            select(BillingRecord)
            .where(BillingRecord.id == record_id)
            .with_for_update()
        )
        if record is None:
            raise NotFoundError(f"billing record not found: {record_id}")
        if record.payment_status is target:
            return record
        if record.payment_status is not PaymentStatus.UNPAID:
            raise BusinessRuleError(
                f"billing record in {record.payment_status.value} cannot transition "
                f"to {target.value}"
            )

        previous_status = record.payment_status
        record.payment_status = target
        self._session.add(
            AuditLog(
                operator_id=operator_id,
                action=action,
                target_type="BillingRecord",
                target_id=record.id,
                before_value={
                    "payment_status": previous_status.value,
                    "fee_amount": str(record.fee_amount),
                },
                after_value={
                    "payment_status": target.value,
                    "fee_amount": str(record.fee_amount),
                },
                reason=None,
            )
        )
        self._session.commit()
        self._session.refresh(record)
        return record

    @staticmethod
    def _local_day_start_utc(value: date) -> datetime:
        local_start = datetime.combine(value, time.min, tzinfo=UTC_PLUS_8)
        return local_start.astimezone(timezone.utc)
