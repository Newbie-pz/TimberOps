"""Top-level API router."""

from typing import Annotated, Literal, TypedDict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api import metrics
from app.api.v1 import (
    ai,
    audit,
    auth,
    billing,
    customers,
    dashboard,
    export,
    reports,
    users,
    vehicles,
    weighing,
)
from app.db.session import engine
from app.observability.health import ReadinessService


class HealthResponse(TypedDict):
    """Shape of the unauthenticated service health response."""

    status: Literal["ok"]
    service: str


def get_readiness_service() -> ReadinessService:
    """Bind readiness checks to the process-wide application Engine."""
    return ReadinessService(engine)


api_router = APIRouter()
api_router.include_router(metrics.router)
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth.router)
v1_router.include_router(users.router)
v1_router.include_router(vehicles.router)
v1_router.include_router(customers.router)
v1_router.include_router(weighing.router)
v1_router.include_router(dashboard.router)
v1_router.include_router(billing.router)
v1_router.include_router(audit.router)
v1_router.include_router(reports.router)
v1_router.include_router(export.router)
v1_router.include_router(ai.router)
api_router.include_router(v1_router)


@api_router.get("/health", tags=["system"])
def health_check() -> HealthResponse:
    """Report process health without requiring a database connection."""
    return {
        "status": "ok",
        "service": "TimberOps backend",
    }


@api_router.get("/ready", tags=["system"])
def readiness_check(
    service: Annotated[ReadinessService, Depends(get_readiness_service)],
) -> JSONResponse:
    """Report whether the backend can safely receive business traffic."""
    result = service.check()
    return JSONResponse(
        status_code=200 if result.is_ready else 503,
        content=result.to_payload(),
    )
