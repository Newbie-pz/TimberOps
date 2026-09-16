"""User persistence constraints."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User


def test_user_is_active_by_default(db_session: Session) -> None:
    user = User(
        username="operator",
        password_hash="$2b$12$not-a-real-hash-for-model-test",
        real_name="磅房操作员",
    )
    db_session.add(user)
    db_session.commit()

    assert user.is_active is True


def test_username_is_unique(db_session: Session) -> None:
    db_session.add_all(
        [
            User(username="operator", password_hash="hash-1", real_name="操作员一"),
            User(username="operator", password_hash="hash-2", real_name="操作员二"),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
