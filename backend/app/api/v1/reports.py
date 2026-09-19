"""Periodic business reports and XLSX downloads."""

from datetime import date
from io import BytesIO
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.report import BusinessReport
from app.security.permissions import require_permission
from app.services.report_service import ReportService


router = APIRouter(prefix="/reports", tags=["Reports"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/daily", response_model=BusinessReport, summary="Daily business report")
def daily_report(
    session: DbSession,
    _current_user: Annotated[
        User,
        Depends(require_permission("report:view")),
    ],
    report_date: date | None = None,
) -> BusinessReport:
    return ReportService(session).daily(report_date)


@router.get(
    "/monthly",
    response_model=BusinessReport,
    summary="Monthly business report",
)
def monthly_report(
    session: DbSession,
    _current_user: Annotated[
        User,
        Depends(require_permission("report:view")),
    ],
    year: int | None = None,
    month: int | None = None,
) -> BusinessReport:
    return ReportService(session).monthly(year=year, month=month)


@router.get(
    "/export",
    summary="Export a business report",
    description="Download the requested daily or monthly report as XLSX.",
)
def export_report(
    session: DbSession,
    _current_user: Annotated[
        User,
        Depends(require_permission("report:export")),
    ],
    report_type: Literal["daily", "monthly"],
    report_date: date | None = None,
    year: int | None = None,
    month: int | None = None,
) -> StreamingResponse:
    service = ReportService(session)
    report = (
        service.daily(report_date)
        if report_type == "daily"
        else service.monthly(year=year, month=month)
    )
    content = service.export_xlsx(report)
    period = (
        report.period_start.strftime("%Y%m%d")
        if report_type == "daily"
        else report.period_start.strftime("%Y%m")
    )
    return StreamingResponse(
        BytesIO(content),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="timberops-{report_type}-{period}.xlsx"'
            )
        },
    )
