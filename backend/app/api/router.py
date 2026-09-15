"""Top-level API router."""

from typing import Literal, TypedDict

from fastapi import APIRouter


class HealthResponse(TypedDict):
    """Shape of the unauthenticated service health response."""

    status: Literal["ok"]
    service: str


api_router = APIRouter()


@api_router.get("/health", tags=["system"])
def health_check() -> HealthResponse:
    """Report process health without requiring a database connection."""
    return {
        "status": "ok",
        "service": "TimberOps backend",
    }
