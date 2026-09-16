"""Weighing task and append-only scale-reading models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.domain.enums import (
    CargoType,
    WeighingDirection,
    WeighingStatus,
    WeightResult,
    WeightSource,
    WeightType,
)

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.vehicle import Vehicle


class WeighingTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Current effective summary and lifecycle of one vehicle weighing job."""

    __tablename__ = "weighing_tasks"
    __table_args__ = (
        CheckConstraint(
            "allowed_gross_weight_tons > 0",
            name="ck_weighing_tasks_allowed_gross_weight_positive",
        ),
        CheckConstraint(
            "tare_weight_tons IS NULL OR tare_weight_tons > 0",
            name="ck_weighing_tasks_tare_positive",
        ),
        CheckConstraint(
            "gross_weight_tons IS NULL OR gross_weight_tons > 0",
            name="ck_weighing_tasks_gross_positive",
        ),
        CheckConstraint(
            "net_weight_tons IS NULL OR net_weight_tons > 0",
            name="ck_weighing_tasks_net_positive",
        ),
        CheckConstraint(
            "overweight_tons >= 0",
            name="ck_weighing_tasks_overweight_nonnegative",
        ),
        CheckConstraint(
            "gross_weight_tons IS NULL OR tare_weight_tons IS NULL "
            "OR gross_weight_tons > tare_weight_tons",
            name="ck_weighing_tasks_gross_above_tare",
        ),
    )

    task_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        index=True,
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        index=True,
    )
    weighing_direction: Mapped[WeighingDirection] = mapped_column(
        Enum(
            WeighingDirection,
            name="weighing_direction",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        default=WeighingDirection.OUTBOUND,
    )
    cargo_type: Mapped[CargoType] = mapped_column(
        Enum(
            CargoType,
            name="cargo_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        )
    )
    cargo_name: Mapped[str | None] = mapped_column(String(100))
    cargo_remark: Mapped[str | None] = mapped_column(Text)
    driver_name_snapshot: Mapped[str | None] = mapped_column(String(100))
    driver_phone_snapshot: Mapped[str | None] = mapped_column(String(32))
    tare_weight_tons: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    gross_weight_tons: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    net_weight_tons: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    allowed_gross_weight_tons: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    overweight_tons: Mapped[Decimal] = mapped_column(
        Numeric(10, 3),
        default=Decimal("0.000"),
    )
    status: Mapped[WeighingStatus] = mapped_column(
        Enum(
            WeighingStatus,
            name="weighing_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        default=WeighingStatus.WAIT_TARE,
        index=True,
    )
    weight_result: Mapped[WeightResult] = mapped_column(
        Enum(
            WeightResult,
            name="weight_result",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        default=WeightResult.PENDING,
        index=True,
    )
    tare_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gross_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="weighing_tasks")
    customer: Mapped["Customer | None"] = relationship(back_populates="weighing_tasks")
    records: Mapped[list["WeighingRecord"]] = relationship(
        back_populates="weighing_task",
        order_by="WeighingRecord.sequence_no",
    )


class WeighingRecord(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable history of every accepted physical scale reading."""

    __tablename__ = "weighing_records"
    __table_args__ = (
        UniqueConstraint(
            "weighing_task_id",
            "sequence_no",
            name="uq_weighing_records_task_sequence",
        ),
        CheckConstraint(
            "weight_tons > 0",
            name="ck_weighing_records_weight_positive",
        ),
        CheckConstraint(
            "sequence_no > 0",
            name="ck_weighing_records_sequence_positive",
        ),
    )

    weighing_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("weighing_tasks.id", ondelete="RESTRICT"),
        index=True,
    )
    weight_type: Mapped[WeightType] = mapped_column(
        Enum(
            WeightType,
            name="weight_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        )
    )
    weight_tons: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    sequence_no: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[UUID | None]
    source: Mapped[WeightSource] = mapped_column(
        Enum(
            WeightSource,
            name="weight_source",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        default=WeightSource.MANUAL,
    )
    remark: Mapped[str | None] = mapped_column(Text)

    weighing_task: Mapped[WeighingTask] = relationship(back_populates="records")
