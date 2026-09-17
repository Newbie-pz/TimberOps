"""Structured, redacted HTTP request logging and correlation IDs."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from ipaddress import ip_address
from time import perf_counter
from typing import Any
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings, get_settings
from app.security.jwt import TokenValidationError, decode_access_token


logger = logging.getLogger("timberops.http")
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


def configure_request_logger() -> None:
    """Ensure request JSON reaches container stdout exactly once."""
    if not any(
        getattr(handler, "_timberops_request_json", False)
        for handler in logger.handlers
    ):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler._timberops_request_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class RequestLoggingMiddleware:
    """Add a correlation ID and emit one safe JSON lifecycle record per request."""

    def __init__(self, app: ASGIApp, settings: Settings | None = None) -> None:
        self.app = app
        self.settings = settings or get_settings()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = _resolve_request_id(headers.get("x-request-id"))
        state: dict[str, Any] = scope.setdefault("state", {})
        state["request_id"] = request_id
        user_id, username = _resolve_token_identity(
            headers.get("authorization"),
            settings=self.settings,
        )
        started_at = perf_counter()
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            record: dict[str, object] = {
                "event": "http_request",
                "timestamp": timestamp,
                "request_id": request_id,
                "method": scope.get("method", ""),
                "path": scope.get("path", ""),
                "status_code": status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
                "username": username,
                "client_ip": _resolve_client_ip(scope, headers),
            }
            logger.log(_level_for_status(status_code), _serialize(record))
            if duration_ms > self.settings.slow_request_threshold_ms:
                slow_record = {
                    **record,
                    "event": "slow_request",
                    "slow_request_threshold_ms": (
                        self.settings.slow_request_threshold_ms
                    ),
                }
                logger.warning(_serialize(slow_record))


def _resolve_request_id(candidate: str | None) -> str:
    """Reuse only bounded, printable request IDs to prevent log/header injection."""
    if candidate and REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid4())


def _resolve_token_identity(
    authorization: str | None,
    *,
    settings: Settings,
) -> tuple[str | None, str | None]:
    """Read signed identity claims without querying the database or leaking tokens."""
    if not authorization:
        return None, None
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token:
        return None, None
    try:
        claims = decode_access_token(token, settings=settings)
    except (TokenValidationError, RuntimeError):
        return None, None
    return str(claims.sub), claims.username


def _resolve_client_ip(scope: Scope, headers: Headers) -> str | None:
    """Prefer Nginx's validated single IP and fall back to the direct peer."""
    forwarded = headers.get("x-real-ip")
    if forwarded:
        try:
            return str(ip_address(forwarded))
        except ValueError:
            pass
    client = scope.get("client")
    if client:
        return str(client[0])
    return None


def _level_for_status(status_code: int) -> int:
    if status_code >= 500:
        return logging.ERROR
    if status_code >= 400:
        return logging.WARNING
    return logging.INFO


def _serialize(record: dict[str, object]) -> str:
    return json.dumps(record, ensure_ascii=False, separators=(",", ":"))
