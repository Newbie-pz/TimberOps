"""Authenticated operations dashboard endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardOverview
from app.security.permissions import require_permission
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(
    session: DbSession,
    _current_user: Annotated[
        User,
        Depends(require_permission("dashboard:view")),
    ],
) -> DashboardOverview:
    """Return the read-only operational overview for authorized staff."""
    return DashboardService(session).get_overview()
