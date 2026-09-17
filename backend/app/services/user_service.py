"""User registration and credential verification service."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.domain.exceptions import AuthenticationError, ConflictError
from app.models.user import User
from app.models.rbac import UserRole
from app.schemas.auth import UserRegister
from app.security.password import hash_password, verify_password


_DUMMY_PASSWORD_HASH = hash_password("timberops-invalid-user-dummy-password")


class UserService:
    """Own account persistence without exposing password hashes to API schemas."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def register(self, data: UserRegister) -> User:
        existing = self._session.scalar(
            select(User.id).where(User.username == data.username)
        )
        if existing is not None:
            raise ConflictError("username already exists")

        user = User(
            username=data.username,
            password_hash=hash_password(data.password),
            real_name=data.real_name,
            is_active=True,
        )
        self._session.add(user)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("username already exists") from exc
        self._session.refresh(user)
        return user

    def list_users(self) -> list[User]:
        """List users with roles eagerly loaded for the admin screen."""
        return list(
            self._session.scalars(
                select(User)
                .options(selectinload(User.role_links).selectinload(UserRole.role))
                .order_by(User.created_at, User.id)
            )
        )

    def authenticate(self, *, username: str, password: str) -> User:
        user = self._session.scalar(
            select(User).where(User.username == username)
        )
        password_hash = (
            user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        )
        password_matches = verify_password(password, password_hash)
        if user is None or not user.is_active or not password_matches:
            raise AuthenticationError("用户名或密码错误")
        return user
