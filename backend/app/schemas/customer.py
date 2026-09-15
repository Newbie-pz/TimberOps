"""Pydantic schemas for the minimal customer record."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerCreate(BaseModel):
    """Data accepted when creating a customer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    contact_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    remark: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be empty")
        return value


class CustomerUpdate(BaseModel):
    """Fields that may be changed on a customer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=200)
    contact_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    remark: str | None = None

    @field_validator("name")
    @classmethod
    def validate_optional_name(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            raise ValueError("name must not be empty")
        return value


class CustomerRead(BaseModel):
    """Customer representation returned by application boundaries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    contact_name: str | None
    phone: str | None
    remark: str | None
    created_at: datetime
    updated_at: datetime
