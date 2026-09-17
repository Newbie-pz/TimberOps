"""Read models for immutable audit events."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    """Audit event enriched with the operator's current display name."""

    id: UUID
    operator_id: UUID | None
    operator_name: str | None
    action: str
    target_type: str
    target_id: UUID | None
    target_display: str | None
    reason: str | None
    before_value: dict[str, Any] | None
    after_value: dict[str, Any] | None
    created_at: datetime
