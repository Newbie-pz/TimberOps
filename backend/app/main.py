"""FastAPI application factory and ASGI entry point."""

from fastapi import FastAPI

from app.api.exceptions import register_exception_handlers
from app.api.router import api_router
from app.core.config import get_settings
from app.integrations.ai.observability import AIRequestObservabilityMiddleware


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )
    register_exception_handlers(application)
    application.include_router(api_router)
    application.add_middleware(AIRequestObservabilityMiddleware)
    return application


app = create_app()
