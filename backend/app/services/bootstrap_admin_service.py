"""Transactional, one-time bootstrap of the first ADMIN account."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.rbac_catalog import PERMISSION_DEFINITIONS, ROLE_DEFINITIONS
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.schemas.auth import UserRegister
from app.security.password import hash_password, verify_password
from app.services.rbac_service import RBACService


class BootstrapAdminError(RuntimeError):
    """Base failure for safe, expected bootstrap refusal."""


class AdminAlreadyExistsError(BootstrapAdminError):
    """The one-time bootstrap has already been consumed."""


class ExistingUserPasswordError(BootstrapAdminError):
    """An existing account could not be safely promoted."""


class RBACDataIncompleteError(BootstrapAdminError):
    """Seeded roles, permissions, or ADMIN grants are incomplete."""


@dataclass(frozen=True)
class BootstrapAdminResult:
    user: User
    user_created: bool


class BootstrapAdminService:
    """Create or promote exactly one first ADMIN in a single transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def assert_bootstrap_available(self) -> None:
        """Provide a fast pre-prompt check; bootstrap performs a locked recheck."""
        self._require_rbac_data()
        if self._admin_exists():
            raise AdminAlreadyExistsError("an ADMIN user already exists.")

    def bootstrap(
        self,
        *,
        username: str,
        real_name: str,
        password: str,
    ) -> BootstrapAdminResult:
        data = UserRegister(
            username=username,
            real_name=real_name,
            password=password,
        )
        try:
            with self._session.begin():
                admin_role = self._lock_and_validate_admin_role()
                if self._admin_exists():
                    raise AdminAlreadyExistsError(
                        "an ADMIN user already exists."
                    )

                user = self._session.scalar(
                    select(User).where(User.username == data.username)
                )
                user_created = user is None
                if user is None:
                    user = User(
                        username=data.username,
                        password_hash=hash_password(data.password),
                        real_name=data.real_name,
                        is_active=True,
                    )
                    self._session.add(user)
                    self._session.flush()
                elif not user.is_active:
                    raise BootstrapAdminError("existing user is inactive.")
                elif not verify_password(data.password, user.password_hash):
                    raise ExistingUserPasswordError(
                        "existing user password verification failed."
                    )

                RBACService(self._session).assign_role(
                    user.id,
                    admin_role.id,
                    commit=False,
                )
        except IntegrityError as exc:
            self._session.rollback()
            raise BootstrapAdminError(
                "bootstrap failed due to a concurrent database conflict."
            ) from exc

        return BootstrapAdminResult(user=user, user_created=user_created)

    def _lock_and_validate_admin_role(self) -> Role:
        admin_role = self._session.scalar(
            select(Role).where(Role.name == "ADMIN").with_for_update()
        )
        if admin_role is None:
            raise RBACDataIncompleteError("RBAC base data is incomplete.")
        self._require_rbac_data()
        return admin_role

    def _require_rbac_data(self) -> None:
        expected_roles = {name for name, _ in ROLE_DEFINITIONS}
        actual_roles = set(self._session.scalars(select(Role.name)))
        expected_permissions = {code for code, _ in PERMISSION_DEFINITIONS}
        actual_permissions = set(self._session.scalars(select(Permission.code)))
        admin_permissions = set(
            self._session.scalars(
                select(Permission.code)
                .join(
                    RolePermission,
                    RolePermission.permission_id == Permission.id,
                )
                .join(Role, Role.id == RolePermission.role_id)
                .where(Role.name == "ADMIN")
            )
        )
        if (
            not expected_roles.issubset(actual_roles)
            or not expected_permissions.issubset(actual_permissions)
            or not expected_permissions.issubset(admin_permissions)
        ):
            raise RBACDataIncompleteError("RBAC base data is incomplete.")

    def _admin_exists(self) -> bool:
        admin_user_id = self._session.scalar(
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.name == "ADMIN")
            .limit(1)
        )
        return admin_user_id is not None
