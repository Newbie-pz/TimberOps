"""Authentication request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_username(value: str) -> str:
    username = value.strip().lower()
    if not username:
        raise ValueError("username must not be empty")
    return username


def _validate_bcrypt_password(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("password must not exceed 72 UTF-8 bytes")
    return value


class UserRegister(BaseModel):
    """Fields accepted when creating a local account."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=72, repr=False)
    real_name: str = Field(min_length=1, max_length=100)

    _normalize_username = field_validator("username")(_normalize_username)
    _validate_password = field_validator("password")(_validate_bcrypt_password)


class UserLogin(BaseModel):
    """JSON login credentials."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=72, repr=False)

    _normalize_username = field_validator("username")(_normalize_username)
    _validate_password = field_validator("password")(_validate_bcrypt_password)


class UserRead(BaseModel):
    """Public user fields; password_hash is intentionally absent."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    real_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    """Bearer access token returned after successful authentication."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
