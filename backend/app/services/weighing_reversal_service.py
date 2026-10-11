"""Transactional compensation workflow for immutable completed weighings."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import PaymentStatus, WeighingStatus
from app.domain.exceptions import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    PaidWeighingRequiresRefundError,
)
from app.models.audit_log import AuditLog
from app.models.billing import BillingRecord
from app.models.weighing import WeighingTask
from app.models.weighing_reversal import WeighingReversal
from app.observability.metrics import record_weighing_reversal
from app.schemas.weighing_reversal import WeighingReversalCreate


class WeighingReversalService:
    """Create at most one reversal without changing the original business fact."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def reverse(
        self,
        task_id: UUID,
        data: WeighingReversalCreate,
        *,
        operator_id: UUID,
    ) -> WeighingReversal:
        task = self._session.scalar(
            select(WeighingTask)
            .where(
                WeighingTask.id == task_id,
                WeighingTask.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if task is None:
            raise NotFoundError(f"weighing task not found: {task_id}")
        if task.status is not WeighingStatus.COMPLETED:
            raise InvalidStateError("only a COMPLETED weighing task can be reversed")

        existing = self._get_by_task_id(task.id)
        if existing is not None:
            return existing

        billing_record = self._session.scalar(
            select(BillingRecord).where(BillingRecord.weighing_task_id == task.id)
        )
        if (
            billing_record is not None
            and billing_record.payment_status is PaymentStatus.PAID
        ):
            raise PaidWeighingRequiresRefundError(
                "已支付费用的称重任务需先建立退款流程，当前不能直接冲正"
            )

        reversal = WeighingReversal(
            original_task_id=task.id,
            reason=data.reason,
            created_by=operator_id,
            billing_record_id=(billing_record.id if billing_record else None),
            billing_payment_status_snapshot=(
                billing_record.payment_status if billing_record else None
            ),
            billing_fee_amount_snapshot=(
                billing_record.fee_amount if billing_record else None
            ),
        )
        self._session.add(reversal)
        try:
            # PostgreSQL may surface the unique-key race during flush rather
            # than commit, so both operations belong to the recovery boundary.
            self._session.flush()
            self._session.add(
                AuditLog(
                    operator_id=operator_id,
                    action="WEIGHING_REVERSED",
                    target_type="WeighingTask",
                    target_id=task.id,
                    before_value={"reversed": False, "status": task.status.value},
                    after_value={
                        "reversed": True,
                        "reversal_id": str(reversal.id),
                        "status": task.status.value,
                        "billing_payment_status": (
                            billing_record.payment_status.value
                            if billing_record
                            else None
                        ),
                    },
                    reason=data.reason,
                )
            )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            concurrent = self._get_by_task_id(task.id)
            if concurrent is not None:
                return concurrent
            raise ConflictError("could not reverse weighing task") from exc

        record_weighing_reversal()
        return self._get_by_task_id(task.id, required=True)

    def _get_by_task_id(
        self,
        task_id: UUID,
        *,
        required: bool = False,
    ) -> WeighingReversal | None:
        reversal = self._session.scalar(
            select(WeighingReversal)
            .options(selectinload(WeighingReversal.creator))
            .where(WeighingReversal.original_task_id == task_id)
        )
        if required and reversal is None:  # pragma: no cover - committed invariant
            raise ConflictError("committed reversal could not be reloaded")
        return reversal
