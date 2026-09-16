"""Customer persistence model."""

from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.weighing import WeighingTask


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Minimal customer record optionally associated with weighing tasks."""

    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(200), index=True)
    contact_name: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    remark: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    weighing_tasks: Mapped[list["WeighingTask"]] = relationship(
        back_populates="customer"
    )
