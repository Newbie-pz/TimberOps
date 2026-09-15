"""Translate domain errors into the public API error envelope."""

from typing import TypedDict

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    BusinessRuleError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationError,
)
from app.integrations.ai.exceptions import AIServiceUnavailableError


class ErrorBody(TypedDict):
    code: str
    message: str


class ErrorEnvelope(TypedDict):
    error: ErrorBody


def _error_response(*, status_code: int, code: str, message: str) -> JSONResponse:
    payload: ErrorEnvelope = {"error": {"code": code, "message": message}}
    return JSONResponse(status_code=status_code, content=payload)


async def resource_not_found_handler(
    request: Request,
    exc: NotFoundError,
) -> JSONResponse:
    del request
    return _error_response(
        status_code=status.HTTP_404_NOT_FOUND,
        code="RESOURCE_NOT_FOUND",
        message=str(exc),
    )


async def invalid_state_handler(
    request: Request,
    exc: InvalidStateError,
) -> JSONResponse:
    del request
    return _error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="INVALID_STATE",
        message=str(exc),
    )


async def business_conflict_handler(
    request: Request,
    exc: ConflictError | BusinessRuleError | ValidationError,
) -> JSONResponse:
    del request
    return _error_response(
        status_code=status.HTTP_409_CONFLICT,
        code="BUSINESS_CONFLICT",
        message=str(exc),
    )


async def ai_service_unavailable_handler(
    request: Request,
    exc: AIServiceUnavailableError,
) -> JSONResponse:
    """Return a stable error envelope when the optional AI service is disabled."""
    del request
    return _error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="AI_SERVICE_UNAVAILABLE",
        message=str(exc),
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Register handlers once when constructing the application."""
    application.add_exception_handler(NotFoundError, resource_not_found_handler)
    application.add_exception_handler(InvalidStateError, invalid_state_handler)
    application.add_exception_handler(ConflictError, business_conflict_handler)
    application.add_exception_handler(BusinessRuleError, business_conflict_handler)
    application.add_exception_handler(ValidationError, business_conflict_handler)
    application.add_exception_handler(
        AIServiceUnavailableError,
        ai_service_unavailable_handler,
    )
