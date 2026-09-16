"""Shared commands for auditable soft deletion."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeleteEntityInput(BaseModel):
    """Deletion reason plus an optional authenticated operator placeholder."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=1)
    operator_id: UUID | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason is required")
        return value
