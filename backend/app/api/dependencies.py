"""Reusable API dependencies for authenticated endpoints."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.domain.exceptions import AuthenticationError
from app.models.user import User
from app.security.jwt import TokenValidationError, decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)
SettingsDependency = Annotated[Settings, Depends(get_settings)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def get_security_session_factory() -> sessionmaker[Session]:
    """Provide short-lived sessions for authentication and authorization only."""
    return SessionLocal


SecuritySessionFactory = Annotated[
    sessionmaker[Session],
    Depends(get_security_session_factory),
]


def get_current_user(
    settings: SettingsDependency,
    credentials: BearerCredentials,
    session_factory: SecuritySessionFactory,
) -> User:
    """Resolve an active user from a verified Bearer access token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("缺少有效的 Bearer Token")
    try:
        claims = decode_access_token(credentials.credentials, settings=settings)
    except TokenValidationError as exc:
        raise AuthenticationError("Token 无效或已过期") from exc

    with session_factory() as session:
        user = session.scalar(
            select(User).where(
                User.id == claims.sub,
                User.username == claims.username,
                User.is_active.is_(True),
            )
        )
        if user is None:
            raise AuthenticationError("Token 对应的用户不存在或已停用")
        session.expunge(user)
        return user
