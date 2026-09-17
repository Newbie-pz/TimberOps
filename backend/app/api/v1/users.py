"""Administrator-managed user-role assignment endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import UserAdminRead
from app.schemas.rbac import RoleRead, UserRoleAssign, UserRoleRead
from app.security.permissions import require_permission
from app.services.rbac_service import RBACService
from app.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["users"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "",
    response_model=list[UserAdminRead],
    dependencies=[Depends(require_permission("user:manage"))],
)
def list_users(session: DbSession) -> list[UserAdminRead]:
    return [
        UserAdminRead(
            id=user.id,
            username=user.username,
            real_name=user.real_name,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
            roles=[
                RoleRead.model_validate(link.role)
                for link in sorted(user.role_links, key=lambda item: item.role.name)
            ],
        )
        for user in UserService(session).list_users()
    ]


@router.get(
    "/roles",
    response_model=list[RoleRead],
    dependencies=[Depends(require_permission("user:manage"))],
)
def list_roles(session: DbSession) -> object:
    return RBACService(session).list_roles()


@router.post(
    "/{user_id}/roles",
    response_model=UserRoleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user:manage"))],
)
def assign_user_role(
    user_id: UUID,
    data: UserRoleAssign,
    session: DbSession,
) -> object:
    return RBACService(session).assign_role(user_id, data.role_id)


@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:manage"))],
)
def remove_user_role(
    user_id: UUID,
    role_id: UUID,
    session: DbSession,
) -> None:
    RBACService(session).remove_role(user_id, role_id)
