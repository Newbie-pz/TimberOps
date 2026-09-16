"""Password hashing and JWT primitive tests."""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.security.jwt import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
)
from app.security.password import hash_password, verify_password


TEST_SECRET = "unit-test-jwt-secret-key-with-at-least-32-characters"


def _settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        JWT_SECRET_KEY=TEST_SECRET,
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60,
    )


def test_bcrypt_hashes_are_salted_and_verify_correctly() -> None:
    password = "TimberOps-Secret-123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash) is True
    assert verify_password("wrong-password", first_hash) is False


def test_access_token_can_be_created_and_decoded() -> None:
    user_id = uuid4()

    token = create_access_token(
        user_id=user_id,
        username="operator",
        settings=_settings(),
    )
    claims = decode_access_token(token, settings=_settings())

    assert claims.sub == user_id
    assert claims.username == "operator"


def test_expired_access_token_is_rejected() -> None:
    token = create_access_token(
        user_id=uuid4(),
        username="operator",
        settings=_settings(),
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(TokenValidationError):
        decode_access_token(token, settings=_settings())
