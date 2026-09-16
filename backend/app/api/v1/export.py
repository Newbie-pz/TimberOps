"""Operational spreadsheet export endpoints."""

from datetime import date
from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.enums import CargoType
from app.services.export_service import ExportService
from app.security.permissions import require_permission


router = APIRouter(prefix="/export", tags=["export"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/weighing",
    dependencies=[Depends(require_permission("export:data"))],
)
def export_weighing(
    session: DbSession,
    start_date: date | None = None,
    end_date: date | None = None,
    vehicle_id: UUID | None = None,
    customer_id: UUID | None = None,
    cargo_type: CargoType | None = None,
) -> StreamingResponse:
    """Download filtered weighing history as an XLSX workbook."""
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_date must not be after end_date",
        )
    content = ExportService(session).export_weighing(
        start_date=start_date,
        end_date=end_date,
        vehicle_id=vehicle_id,
        customer_id=customer_id,
        cargo_type=cargo_type,
    )
    filename = f"timberops-weighing-{date.today():%Y%m%d}.xlsx"
    return StreamingResponse(
        BytesIO(content),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
