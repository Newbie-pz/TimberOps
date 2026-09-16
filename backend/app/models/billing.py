"""Billing rule and immutable charge models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.domain.enums import PaymentStatus, VehicleType

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle
    from app.models.weighing import WeighingTask


class BillingRule(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A vehicle fee effective from a point in time."""

    __tablename__ = "billing_rules"
    __table_args__ = (
        UniqueConstraint("vehicle_type", "effective_time", name="uq_billing_rules_type_effective"),
        CheckConstraint("fee_amount >= 0", name="ck_billing_rules_fee_nonnegative"),
    )

    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(
            VehicleType,
            name="billing_rule_vehicle_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        index=True,
    )
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="CNY")
    effective_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class BillingRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One charge snapshot generated exactly once for a completed task."""

    __tablename__ = "billing_records"
    __table_args__ = (
        CheckConstraint("fee_amount >= 0", name="ck_billing_records_fee_nonnegative"),
    )

    weighing_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("weighing_tasks.id", ondelete="RESTRICT"), unique=True, index=True
    )
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), index=True
    )
    vehicle_type_snapshot: Mapped[VehicleType] = mapped_column(
        Enum(
            VehicleType,
            name="billing_record_vehicle_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        )
    )
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", native_enum=False, create_constraint=True, validate_strings=True),
        default=PaymentStatus.UNPAID,
        index=True,
    )

    weighing_task: Mapped["WeighingTask"] = relationship(back_populates="billing_record")
    vehicle: Mapped["Vehicle"] = relationship()
