"""Commands and reads for completed weighing reversals."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import PaymentStatus


class WeighingReversalCreate(BaseModel):
    """Mandatory explanation for a high-risk compensating action."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason must not be blank")
        return value


class WeighingReversalRead(BaseModel):
    """Immutable reversal plus the billing state captured at that moment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_task_id: UUID
    reason: str
    created_by: UUID | None
    operator_name: str | None
    billing_record_id: UUID | None
    billing_payment_status_snapshot: PaymentStatus | None
    billing_fee_amount_snapshot: Decimal | None
    created_at: datetime
