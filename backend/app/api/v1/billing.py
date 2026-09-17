"""Billing record queries and audited payment-state operations."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import PaymentStatus
from app.models.user import User
from app.schemas.billing import BillingRecordListItem, BillingRecordRead
from app.security.permissions import require_permission
from app.services.billing_service import BillingService


router = APIRouter(prefix="/billing", tags=["billing"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/records", response_model=list[BillingRecordListItem])
def list_billing_records(
    session: DbSession,
    _current_user: Annotated[
        User,
        Depends(require_permission("billing:view")),
    ],
    start_date: date | None = None,
    end_date: date | None = None,
    vehicle_id: UUID | None = None,
    customer_id: UUID | None = None,
    payment_status: PaymentStatus | None = None,
) -> list[BillingRecordListItem]:
    return BillingService(session).list_records(
        start_date=start_date,
        end_date=end_date,
        vehicle_id=vehicle_id,
        customer_id=customer_id,
        payment_status=payment_status,
    )


@router.patch("/records/{record_id}/pay", response_model=BillingRecordRead)
def pay_billing_record(
    record_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(require_permission("billing:update")),
    ],
) -> object:
    return BillingService(session).mark_paid(
        record_id,
        operator_id=current_user.id,
    )


@router.patch("/records/{record_id}/waive", response_model=BillingRecordRead)
def waive_billing_record(
    record_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(require_permission("billing:waive")),
    ],
) -> object:
    return BillingService(session).waive(
        record_id,
        operator_id=current_user.id,
    )
