"""Short-lived JWT access-token creation and validation."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.core.config import Settings, get_settings


JWT_ALGORITHM = "HS256"


class TokenValidationError(ValueError):
    """A token is expired, malformed, or fails signature/claim validation."""


@dataclass(frozen=True)
class AccessTokenClaims:
    """Validated claims used by the authentication dependency."""

    sub: UUID
    username: str
    exp: datetime


def create_access_token(
    *,
    user_id: UUID,
    username: str,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    now: datetime | None = None,
) -> str:
    """Create an HMAC-signed access token containing only identity claims."""
    active_settings = settings or get_settings()
    issued_at = now or datetime.now(timezone.utc)
    lifetime = expires_delta or timedelta(
        minutes=active_settings.jwt_access_token_expire_minutes
    )
    expires_at = issued_at + lifetime
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        active_settings.require_jwt_secret_key(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(
    token: str,
    *,
    settings: Settings | None = None,
) -> AccessTokenClaims:
    """Verify signature, expiration, and required identity claims."""
    active_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            active_settings.require_jwt_secret_key(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "username", "exp"]},
        )
        subject = UUID(str(payload["sub"]))
        username = str(payload["username"])
        expires_at = datetime.fromtimestamp(float(payload["exp"]), tz=timezone.utc)
        if not username:
            raise ValueError("username claim is empty")
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError("invalid or expired access token") from exc

    return AccessTokenClaims(sub=subject, username=username, exp=expires_at)
