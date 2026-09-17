"""Top-level API router."""

from typing import Literal, TypedDict

from fastapi import APIRouter

from app.api.v1 import (
    ai,
    audit,
    auth,
    billing,
    customers,
    dashboard,
    export,
    users,
    vehicles,
    weighing,
)


class HealthResponse(TypedDict):
    """Shape of the unauthenticated service health response."""

    status: Literal["ok"]
    service: str


api_router = APIRouter()
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth.router)
v1_router.include_router(users.router)
v1_router.include_router(vehicles.router)
v1_router.include_router(customers.router)
v1_router.include_router(weighing.router)
v1_router.include_router(dashboard.router)
v1_router.include_router(billing.router)
v1_router.include_router(audit.router)
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
