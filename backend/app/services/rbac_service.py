"""Role assignment and real-time permission query service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


class RBACService:
    """Keep authorization data normalized and queried from the database."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_user_roles(self, user_id: UUID) -> list[Role]:
        self._require_user(user_id)
        return list(
            self._session.scalars(
                select(Role)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
                .order_by(Role.name)
            )
        )

    def list_user_permissions(self, user_id: UUID) -> list[Permission]:
        self._require_user(user_id)
        return list(
            self._session.scalars(
                select(Permission)
                .join(
                    RolePermission,
                    RolePermission.permission_id == Permission.id,
                )
                .join(UserRole, UserRole.role_id == RolePermission.role_id)
                .where(UserRole.user_id == user_id)
                .distinct()
                .order_by(Permission.code)
            )
        )

    def has_permission(self, user_id: UUID, permission_code: str) -> bool:
        permission_id = self._session.scalar(
            select(Permission.id)
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.id,
            )
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(
                UserRole.user_id == user_id,
                Permission.code == permission_code,
            )
            .limit(1)
        )
        return permission_id is not None

    def assign_role(
        self,
        user_id: UUID,
        role_id: UUID,
        *,
        commit: bool = True,
    ) -> UserRole:
        self._require_user(user_id)
        self._require_role(role_id)
        assignment = UserRole(user_id=user_id, role_id=role_id)
        self._session.add(assignment)
        if not commit:
            self._session.flush()
            return assignment
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("role is already assigned to the user") from exc
        self._session.refresh(assignment)
        return assignment

    def remove_role(self, user_id: UUID, role_id: UUID) -> None:
        assignment = self._session.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        )
        if assignment is None:
            raise NotFoundError("user role assignment not found")
        role = self._session.scalar(
            select(Role).where(Role.id == role_id).with_for_update()
        )
        if role is None:
            raise NotFoundError(f"role not found: {role_id}")
        if role.name == "ADMIN":
            admin_count = self._session.scalar(
                select(func.count(UserRole.id)).where(
                    UserRole.role_id == role_id
                )
            )
            if int(admin_count or 0) <= 1:
                raise BusinessRuleError(
                    "the last ADMIN role assignment cannot be removed"
                )
        self._session.delete(assignment)
        self._session.commit()

    def _require_user(self, user_id: UUID) -> User:
        user = self._session.get(User, user_id)
        if user is None:
            raise NotFoundError(f"user not found: {user_id}")
        return user

    def _require_role(self, role_id: UUID) -> Role:
        role = self._session.get(Role, role_id)
        if role is None:
            raise NotFoundError(f"role not found: {role_id}")
        return role
