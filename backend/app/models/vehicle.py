"""Vehicle persistence model."""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.weighing import WeighingTask


class Vehicle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A registered vehicle and its current allowed gross-weight limit."""

    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint(
            "allowed_gross_weight_tons > 0",
            name="ck_vehicles_allowed_gross_weight_positive",
        ),
    )

    plate_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    driver_name: Mapped[str | None] = mapped_column(String(100))
    driver_phone: Mapped[str | None] = mapped_column(String(32))
    vehicle_type: Mapped[str | None] = mapped_column(String(50))
    allowed_gross_weight_tons: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    remark: Mapped[str | None] = mapped_column(Text)

    weighing_tasks: Mapped[list["WeighingTask"]] = relationship(
        back_populates="vehicle"
    )
