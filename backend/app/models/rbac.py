"""Normalized role-based access-control persistence models."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named collection of permissions assignable to users."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    user_links: Mapped[list["UserRole"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )
    permission_links: Mapped[list["RolePermission"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )


class Permission(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One stable authorization capability identified by a unique code."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    role_links: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class UserRole(UUIDPrimaryKeyMixin, Base):
    """Many-to-many assignment between users and roles."""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        index=True,
    )

    user: Mapped["User"] = relationship(back_populates="role_links")
    role: Mapped[Role] = relationship(back_populates="user_links")


class RolePermission(UUIDPrimaryKeyMixin, Base):
    """Many-to-many grant between roles and permissions."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_permission",
        ),
    )

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        index=True,
    )
    permission_id: Mapped[UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"),
        index=True,
    )

    role: Mapped[Role] = relationship(back_populates="permission_links")
    permission: Mapped[Permission] = relationship(back_populates="role_links")
