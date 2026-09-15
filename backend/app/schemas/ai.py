"""Public request and response contracts for the read-only AI Agent."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIChatRequest(BaseModel):
    """One stateless question for the TimberOps business assistant."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class AIToolCallRead(BaseModel):
    """Safe execution metadata; never includes model reasoning or database output."""

    name: str
    arguments: dict[str, Any]
    status: Literal["completed", "failed", "requested"]


class AIChatResponse(BaseModel):
    """Final answer and inspectable business tool decisions."""

    answer: str
    tool_calls: list[AIToolCallRead]
