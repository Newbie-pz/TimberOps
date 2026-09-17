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


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    active_settings = settings or get_settings()
    configure_request_logger()
    docs_enabled = active_settings.enable_api_docs
    application = FastAPI(
        title=active_settings.app_name,
        debug=active_settings.debug,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
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
    )
    return application


app = create_app()
