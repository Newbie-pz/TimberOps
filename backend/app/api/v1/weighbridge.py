"""Authenticated, read-only weighbridge device endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.integrations.weighbridge.base import WeighbridgeAdapter
from app.schemas.weighbridge import WeighbridgeStatusRead, WeightReadingRead
from app.security.permissions import require_permission
from app.services.weighbridge_service import WeighbridgeService

router = APIRouter(prefix="/weighbridge", tags=["Weighbridge"])


def get_weighbridge_adapter(request: Request) -> WeighbridgeAdapter:
    """Return the process-local adapter built during application startup."""
    return request.app.state.weighbridge_adapter


AdapterDependency = Annotated[WeighbridgeAdapter, Depends(get_weighbridge_adapter)]


@router.get(
    "/status",
    response_model=WeighbridgeStatusRead,
    dependencies=[Depends(require_permission("weighing:view"))],
    summary="Get weighbridge device status",
)
def get_status(adapter: AdapterDependency) -> WeighbridgeStatusRead:
    """Report device capability; offline is not application un-readiness."""
    return WeighbridgeStatusRead.model_validate(
        WeighbridgeService(adapter).get_status()
    )


@router.get(
    "/weight",
    response_model=WeightReadingRead,
    dependencies=[Depends(require_permission("weighing:view"))],
    summary="Read current weighbridge weight",
)
def get_weight(adapter: AdapterDependency) -> WeightReadingRead:
    """Return a transient reading without creating or changing business data."""
    return WeightReadingRead.model_validate(
        WeighbridgeService(adapter).read_weight()
    )
