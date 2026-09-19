"""Weighing task REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.cargo_catalog import get_cargo_catalog
from app.domain.enums import CargoType, PaymentStatus, WeighingStatus
from app.models.user import User
from app.schemas.lifecycle import DeleteEntityInput
from app.schemas.weighing import (
    GrossWeightInput,
    ReweighInput,
    TaskDetailResponse,
    TareWeightInput,
    WeighingRecordRead,
    WeighingTaskCreate,
    WeighingTaskRead,
)
from app.security.permissions import require_permission
from app.services.weighing_service import WeighingService


router = APIRouter(prefix="/weighing", tags=["Weighing"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/cargo-catalog",
    response_model=dict[str, list[str]],
    dependencies=[Depends(require_permission("weighing:view"))],
)
def cargo_catalog() -> dict[str, list[str]]:
    """Expose the domain-owned cargo-name choices to entry clients."""
    return get_cargo_catalog()


@router.post(
    "/tasks",
    response_model=WeighingTaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a weighing task",
    description="Create a WAIT_TARE task from active vehicle and optional customer data.",
)
def create_task(
    data: WeighingTaskCreate,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(require_permission("weighing:create")),
    ],
) -> object:
    return WeighingService(session).create_task(data, operator_id=current_user.id)


@router.get(
    "/tasks",
    response_model=list[WeighingTaskRead],
    dependencies=[Depends(require_permission("weighing:view"))],
)
def list_tasks(
    session: DbSession,
    cargo_type: CargoType | None = None,
    status_filter: Annotated[
        WeighingStatus | None,
        Query(alias="status"),
    ] = None,
    vehicle_id: UUID | None = None,
    payment_status: PaymentStatus | None = None,
) -> object:
    return WeighingService(session).list_tasks(
        cargo_type=cargo_type,
        status=status_filter,
        vehicle_id=vehicle_id,
        payment_status=payment_status,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskDetailResponse,
    dependencies=[Depends(require_permission("weighing:view"))],
)
def get_task_detail(task_id: UUID, session: DbSession) -> TaskDetailResponse:
    service = WeighingService(session)
    return TaskDetailResponse(
        task=WeighingTaskRead.model_validate(service.get_task(task_id)),
        records=[
            WeighingRecordRead.model_validate(record)
            for record in service.list_records(task_id)
        ],
    )


@router.get(
    "/tasks/{task_id}/records",
    response_model=list[WeighingRecordRead],
    dependencies=[Depends(require_permission("weighing:view"))],
)
def list_task_records(task_id: UUID, session: DbSession) -> object:
    return WeighingService(session).list_records(task_id)


@router.post(
    "/tasks/{task_id}/tare",
    response_model=WeighingTaskRead,
    summary="Record tare weight",
    description="Append the first manual reading; only WAIT_TARE is accepted.",
)
def record_tare(
    task_id: UUID,
    data: TareWeightInput,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(require_permission("weighing:tare")),
    ],
) -> object:
    return WeighingService(session).record_tare(
        task_id,
        data,
        operator_id=current_user.id,
    )


@router.post(
    "/tasks/{task_id}/loading",
    response_model=WeighingTaskRead,
    dependencies=[Depends(require_permission("weighing:gross"))],
)
def start_loading(task_id: UUID, session: DbSession) -> object:
    """Compatibility endpoint; LOADING was removed and now returns WAIT_GROSS."""
    return WeighingService(session).start_loading(task_id)


@router.post(
    "/tasks/{task_id}/wait-gross",
    response_model=WeighingTaskRead,
    dependencies=[Depends(require_permission("weighing:gross"))],
)
def finish_loading(task_id: UUID, session: DbSession) -> object:
    """Move from completed tare weighing directly to WAIT_GROSS."""
    return WeighingService(session).finish_loading(task_id)


@router.post(
    "/tasks/{task_id}/gross",
    response_model=WeighingTaskRead,
    summary="Record gross weight",
    description="Append the first gross reading and calculate NORMAL or OVERWEIGHT.",
)
def record_gross(
    task_id: UUID,
    data: GrossWeightInput,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(require_permission("weighing:gross")),
    ],
) -> object:
    return WeighingService(session).record_gross(
        task_id,
        data,
        operator_id=current_user.id,
    )


@router.post(
    "/tasks/{task_id}/reweigh",
    response_model=WeighingTaskRead,
    summary="Record an overweight reweigh",
    description="Append a reasoned REWEIGH after an overweight result.",
)
def record_reweigh(
    task_id: UUID,
    data: ReweighInput,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(require_permission("weighing:gross")),
    ],
) -> object:
    return WeighingService(session).record_reweigh(
        task_id,
        data,
        operator_id=current_user.id,
    )


@router.post(
    "/tasks/{task_id}/complete",
    response_model=WeighingTaskRead,
    summary="Complete a normal weighing task",
    description="Complete only GROSS_COMPLETED tasks whose result is NORMAL.",
)
def complete_task(
    task_id: UUID,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(require_permission("weighing:complete")),
    ],
) -> object:
    return WeighingService(session).complete_task(
        task_id,
        operator_id=current_user.id,
    )


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    task_id: UUID,
    data: DeleteEntityInput,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(require_permission("weighing:delete")),
    ],
) -> None:
    WeighingService(session).delete_task(
        task_id,
        data,
        operator_id=current_user.id,
    )
