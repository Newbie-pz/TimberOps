"""FastAPI dependency factory for database-backed permission checks."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_current_user, get_security_session_factory
from app.domain.exceptions import PermissionDeniedError
from app.models.user import User
from app.services.rbac_service import RBACService


def require_permission(permission_code: str) -> Callable[..., User]:
    """Require one permission while resolving grants from the current database."""

    def check_permission(
        current_user: Annotated[User, Depends(get_current_user)],
        session_factory: Annotated[
            sessionmaker[Session],
            Depends(get_security_session_factory),
        ],
    ) -> User:
        with session_factory() as session:
            if not RBACService(session).has_permission(
                current_user.id,
                permission_code,
            ):
                raise PermissionDeniedError("Permission denied")
        return current_user

    return check_permission
