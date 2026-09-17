"""Read schemas for billing snapshots."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.enums import PaymentStatus, VehicleType


class BillingRecordRead(BaseModel):
    """Charge information embedded in a weighing task response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    weighing_task_id: UUID
    vehicle_id: UUID
    vehicle_type_snapshot: VehicleType
    fee_amount: Decimal
    payment_status: PaymentStatus
    created_at: datetime


class BillingRecordListItem(BillingRecordRead):
    """Billing record enriched with immutable operational display context."""

    task_no: str
    plate_number: str
    customer_id: UUID | None
    customer_name: str | None
    completed_at: datetime | None
