"""Weighing task REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.cargo_catalog import get_cargo_catalog
from app.domain.enums import CargoType, WeighingStatus
from app.schemas.weighing import (
    GrossWeightInput,
    ReweighInput,
    TaskDetailResponse,
    TareWeightInput,
    WeighingRecordRead,
    WeighingTaskCreate,
    WeighingTaskRead,
)
from app.services.weighing_service import WeighingService


router = APIRouter(prefix="/weighing", tags=["weighing"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/cargo-catalog", response_model=dict[str, list[str]])
def cargo_catalog() -> dict[str, list[str]]:
    """Expose the domain-owned cargo-name choices to entry clients."""
    return get_cargo_catalog()


@router.post(
    "/tasks",
    response_model=WeighingTaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task(data: WeighingTaskCreate, session: DbSession) -> object:
    return WeighingService(session).create_task(data)


@router.get("/tasks", response_model=list[WeighingTaskRead])
def list_tasks(
    session: DbSession,
    cargo_type: CargoType | None = None,
    status_filter: Annotated[
        WeighingStatus | None,
        Query(alias="status"),
    ] = None,
    vehicle_id: UUID | None = None,
) -> object:
    return WeighingService(session).list_tasks(
        cargo_type=cargo_type,
        status=status_filter,
        vehicle_id=vehicle_id,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def get_task_detail(task_id: UUID, session: DbSession) -> TaskDetailResponse:
    service = WeighingService(session)
    return TaskDetailResponse(
        task=WeighingTaskRead.model_validate(service.get_task(task_id)),
        records=[
            WeighingRecordRead.model_validate(record)
            for record in service.list_records(task_id)
        ],
    )


@router.get("/tasks/{task_id}/records", response_model=list[WeighingRecordRead])
def list_task_records(task_id: UUID, session: DbSession) -> object:
    return WeighingService(session).list_records(task_id)


@router.post("/tasks/{task_id}/tare", response_model=WeighingTaskRead)
def record_tare(
    task_id: UUID,
    data: TareWeightInput,
    session: DbSession,
) -> object:
    return WeighingService(session).record_tare(task_id, data)


@router.post("/tasks/{task_id}/loading", response_model=WeighingTaskRead)
def start_loading(task_id: UUID, session: DbSession) -> object:
    """Compatibility endpoint; LOADING was removed and now returns WAIT_GROSS."""
    return WeighingService(session).start_loading(task_id)


@router.post("/tasks/{task_id}/wait-gross", response_model=WeighingTaskRead)
def finish_loading(task_id: UUID, session: DbSession) -> object:
    """Move from completed tare weighing directly to WAIT_GROSS."""
    return WeighingService(session).finish_loading(task_id)


@router.post("/tasks/{task_id}/gross", response_model=WeighingTaskRead)
def record_gross(
    task_id: UUID,
    data: GrossWeightInput,
    session: DbSession,
) -> object:
    return WeighingService(session).record_gross(task_id, data)


@router.post("/tasks/{task_id}/reweigh", response_model=WeighingTaskRead)
def record_reweigh(
    task_id: UUID,
    data: ReweighInput,
    session: DbSession,
) -> object:
    return WeighingService(session).record_reweigh(task_id, data)


@router.post("/tasks/{task_id}/complete", response_model=WeighingTaskRead)
def complete_task(task_id: UUID, session: DbSession) -> object:
    return WeighingService(session).complete_task(task_id)
