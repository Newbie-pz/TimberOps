"""Registration, JSON login, and current-user endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.domain.exceptions import RegistrationDisabledError
from app.models.user import User
from app.schemas.auth import (
    LoginResponse,
    RegistrationStatusResponse,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.schemas.rbac import PermissionRead, RoleRead
from app.security.jwt import create_access_token
from app.services.rbac_service import RBACService
from app.services.user_service import UserService


router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get(
    "/registration-status",
    response_model=RegistrationStatusResponse,
)
def registration_status(
    settings: SettingsDependency,
) -> RegistrationStatusResponse:
    """Expose only whether anonymous account registration is available."""
    return RegistrationStatusResponse(
        enabled=settings.public_registration_enabled,
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: UserRegister,
    session: DbSession,
    settings: SettingsDependency,
) -> object:
    if not settings.public_registration_enabled:
        raise RegistrationDisabledError("Public registration is disabled")
    return UserService(session).register(data)


@router.post("/login", response_model=LoginResponse)
def login(
    data: UserLogin,
    session: DbSession,
    settings: SettingsDependency,
) -> LoginResponse:
    user = UserService(session).authenticate(
        username=data.username,
        password=data.password,
    )
    return LoginResponse(
        access_token=create_access_token(
            user_id=user.id,
            username=user.username,
            settings=settings,
        ),
        token_type="Bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserRead)
def me(current_user: CurrentUser) -> object:
    return current_user


@router.get("/roles", response_model=list[RoleRead])
def current_user_roles(
    current_user: CurrentUser,
    session: DbSession,
) -> object:
    return RBACService(session).list_user_roles(current_user.id)


@router.get("/permissions", response_model=list[PermissionRead])
def current_user_permissions(
    current_user: CurrentUser,
    session: DbSession,
) -> object:
    return RBACService(session).list_user_permissions(current_user.id)
