"""Administrator-managed user-role assignment endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.rbac import UserRoleAssign, UserRoleRead
from app.security.permissions import require_permission
from app.services.rbac_service import RBACService


router = APIRouter(prefix="/users", tags=["users"])
DbSession = Annotated[Session, Depends(get_db)]


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
