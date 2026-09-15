"""Minimal append-only audit log model."""

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


json_type = JSON().with_variant(JSONB(), "postgresql")


class AuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Security-sensitive action history; no update/delete service is exposed."""

    __tablename__ = "audit_logs"

    operator_id: Mapped[UUID | None] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str] = mapped_column(String(64), index=True)
    target_id: Mapped[UUID | None] = mapped_column(index=True)
    before_value: Mapped[dict[str, Any] | None] = mapped_column(json_type)
    after_value: Mapped[dict[str, Any] | None] = mapped_column(json_type)
    reason: Mapped[str | None] = mapped_column(Text)
