"""Immutable compensation record for a completed weighing business fact."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.domain.enums import PaymentStatus

if TYPE_CHECKING:
    from app.models.billing import BillingRecord
    from app.models.user import User
    from app.models.weighing import WeighingTask


class WeighingReversal(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One append-only reversal; the original task and readings remain unchanged."""

    __tablename__ = "weighing_reversals"
    __table_args__ = (
        UniqueConstraint(
            "original_task_id",
            name="uq_weighing_reversals_original_task",
        ),
        CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_weighing_reversals_reason_not_blank",
        ),
    )

    original_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("weighing_tasks.id", ondelete="RESTRICT"),
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(500))
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    billing_record_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("billing_records.id", ondelete="RESTRICT"),
    )
    billing_payment_status_snapshot: Mapped[PaymentStatus | None] = mapped_column(
        Enum(
            PaymentStatus,
            name="reversal_billing_payment_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        )
    )
    billing_fee_amount_snapshot: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2)
    )

    original_task: Mapped["WeighingTask"] = relationship(back_populates="reversal")
    creator: Mapped["User | None"] = relationship()
    billing_record: Mapped["BillingRecord | None"] = relationship()

    @property
    def operator_name(self) -> str | None:
        return self.creator.real_name if self.creator is not None else None
