"""RBAC persistence constraints and seeded permission matrix."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.rbac_catalog import (
    PERMISSION_DEFINITIONS,
    ROLE_PERMISSION_CODES,
)
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.services.rbac_service import RBACService


def _user_with_role(session: Session, role_name: str, username: str) -> User:
    role = session.scalar(select(Role).where(Role.name == role_name))
    assert role is not None
    user = User(
        username=username,
        password_hash="not-used",
        real_name=username,
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()
    return user


def test_role_can_be_created(db_session: Session) -> None:
    role = Role(name="AUDITOR", description="审计员")
    db_session.add(role)
    db_session.commit()

    assert role.id is not None
    assert role.name == "AUDITOR"


def test_permission_code_is_unique(db_session: Session) -> None:
    db_session.add(
        Permission(code="vehicle:view", name="重复权限", description=None)
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_user_role_pair_is_unique(db_session: Session) -> None:
    role = db_session.scalar(select(Role).where(Role.name == "VIEWER"))
    assert role is not None
    user = User(username="unique_role_user", password_hash="hash", real_name="测试")
    db_session.add(user)
    db_session.flush()
    db_session.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id),
            UserRole(user_id=user.id, role_id=role.id),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_role_permission_pair_is_unique(db_session: Session) -> None:
    role = db_session.scalar(select(Role).where(Role.name == "VIEWER"))
    permission = db_session.scalar(
        select(Permission).where(Permission.code == "vehicle:view")
    )
    assert role is not None
    assert permission is not None
    db_session.add(
        RolePermission(role_id=role.id, permission_id=permission.id)
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize("role_name", ["ADMIN", "OPERATOR", "VIEWER"])
def test_seeded_role_permission_matrix(
    db_session: Session,
    role_name: str,
) -> None:
    user = _user_with_role(
        db_session,
        role_name,
        f"matrix_{role_name.lower()}",
    )

    actual = {
        permission.code
        for permission in RBACService(db_session).list_user_permissions(user.id)
    }

    assert actual == set(ROLE_PERMISSION_CODES[role_name])
    if role_name == "ADMIN":
        assert len(actual) == len(PERMISSION_DEFINITIONS)
    if role_name == "OPERATOR":
        assert "vehicle:delete" not in actual
        assert "user:manage" not in actual
    if role_name == "VIEWER":
        assert all(code.endswith(":view") or code in {"export:data", "ai:query"} for code in actual)
