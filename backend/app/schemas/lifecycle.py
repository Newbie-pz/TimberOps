"""Shared commands for auditable soft deletion."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DeleteEntityInput(BaseModel):
    """Client-supplied deletion reason; operator identity is server-owned."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def ignore_legacy_operator_id(cls, value: Any) -> Any:
        """Accept but discard the old field so clients cannot forge identity."""
        if isinstance(value, dict) and "operator_id" in value:
            sanitized = dict(value)
            sanitized.pop("operator_id", None)
            return sanitized
        return value

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason is required")
        return value
