"""Authorized read-only access to the operational audit trail."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.security.permissions import require_permission
from app.services.audit_service import AuditService


router = APIRouter(prefix="/audit", tags=["Audit"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/logs",
    response_model=list[AuditLogRead],
    summary="Query audit logs",
    description="Read filtered audit events with server-resolved target display values.",
)
def list_audit_logs(
    session: DbSession,
    _current_user: Annotated[
        User,
        Depends(require_permission("audit:view")),
    ],
    start_date: date | None = None,
    end_date: date | None = None,
    operator_id: UUID | None = None,
    action: str | None = None,
    target_type: str | None = None,
) -> list[AuditLogRead]:
    return AuditService(session).list_logs(
        start_date=start_date,
        end_date=end_date,
        operator_id=operator_id,
        action=action,
        target_type=target_type,
    )
