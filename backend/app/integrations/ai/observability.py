"""Request correlation and safe lifecycle logs for the AI HTTP boundary."""

import logging
from time import perf_counter
from typing import Any
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings


logger = logging.getLogger("timberops.ai")


class AIRequestObservabilityMiddleware:
    """Attach a request ID and log metadata without prompts or credentials."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != "/api/v1/ai/chat":
            await self.app(scope, receive, send)
            return

        state: dict[str, Any] = scope.setdefault("state", {})
        owns_request_id = not state.get("request_id")
        request_id = str(state.get("request_id") or uuid4())
        state["request_id"] = request_id
        state["ai_request_id"] = request_id
        settings = get_settings()
        provider = settings.llm_provider
        model = settings.doubao_model or "unconfigured"
        started_at = perf_counter()
        response_status = 500

        logger.info(
            "AI request started request_id=%s provider=%s model=%s",
            request_id,
            provider,
            model,
        )

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
                if owns_request_id:
                    MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            success = response_status < 400
            logger.info(
                "AI request finished request_id=%s provider=%s model=%s "
                "duration_ms=%.2f success=%s error_type=%s "
                "tool_names=%s message_length=%s",
                request_id,
                provider,
                model,
                duration_ms,
                success,
                state.get("ai_error_type", "none"),
                state.get("ai_tool_names", []),
                state.get("ai_message_length", "unknown"),
            )
