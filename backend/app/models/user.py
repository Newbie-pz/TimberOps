"""Enterprise user identity model."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.rbac import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A local account; authorization roles are intentionally out of scope."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    real_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
    )
    role_links: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
