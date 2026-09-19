"""FastAPI application factory and ASGI entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exceptions import register_exception_handlers
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.integrations.ai.observability import AIRequestObservabilityMiddleware
from app.middleware.request_logging import (
    RequestLoggingMiddleware,
    configure_request_logger,
)


OPENAPI_TAGS = [
    {"name": "Auth", "description": "Registration, login, and current identity."},
    {"name": "Users / RBAC", "description": "Administrator-managed users and roles."},
    {"name": "Vehicles", "description": "Vehicle master data and lifecycle."},
    {"name": "Customers", "description": "Customer master data and lifecycle."},
    {"name": "Weighing", "description": "Manual weighing workflow and append-only readings."},
    {"name": "Billing", "description": "Fee records and audited payment states."},
    {"name": "Dashboard", "description": "Current operational overview."},
    {"name": "Reports", "description": "Daily and monthly business reporting."},
    {"name": "Audit", "description": "Read-only operational audit trail."},
    {"name": "Export", "description": "Operational spreadsheet exports."},
    {"name": "AI", "description": "Optional read-only LangGraph assistant."},
    {"name": "System / Observability", "description": "Runtime health and metrics."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    active_settings = settings or get_settings()
    configure_request_logger()
    docs_enabled = active_settings.enable_api_docs
    application = FastAPI(
        title=active_settings.app_name,
        description=(
            "TimberOps vehicle weighing and operations API. Business endpoints "
            "use JWT authentication and backend RBAC unless explicitly documented."
        ),
        version="0.7.0",
        openapi_tags=OPENAPI_TAGS,
        debug=active_settings.debug,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    application.state.settings = active_settings
    register_exception_handlers(application)
    application.include_router(api_router)
    application.add_middleware(AIRequestObservabilityMiddleware)
    allowed_origins = active_settings.get_cors_allowed_origins()
    if allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
            expose_headers=["X-Request-ID"],
        )
    application.add_middleware(
        RequestLoggingMiddleware,
        settings=active_settings,
        routes=tuple(application.routes),
    )
    return application


app = create_app()
