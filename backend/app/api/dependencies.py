"""Reusable API dependencies for authenticated endpoints."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.domain.exceptions import AuthenticationError
from app.models.user import User
from app.security.jwt import TokenValidationError, decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def get_current_user(
    session: DbSession,
    settings: SettingsDependency,
    credentials: BearerCredentials,
) -> User:
    """Resolve an active user from a verified Bearer access token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("缺少有效的 Bearer Token")
    try:
        claims = decode_access_token(credentials.credentials, settings=settings)
    except TokenValidationError as exc:
        raise AuthenticationError("Token 无效或已过期") from exc

    user = session.scalar(
        select(User).where(
            User.id == claims.sub,
            User.username == claims.username,
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise AuthenticationError("Token 对应的用户不存在或已停用")
    return user
