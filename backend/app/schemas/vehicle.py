"""Pydantic schemas for vehicle commands and reads."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PositiveWeight = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=3),
]


def _normalize_plate(value: str) -> str:
    plate_number = value.strip().upper()
    if not plate_number:
        raise ValueError("plate_number must not be empty")
    return plate_number


class VehicleCreate(BaseModel):
    """Data accepted when registering a vehicle."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    plate_number: str = Field(max_length=20)
    driver_name: str | None = Field(default=None, max_length=100)
    driver_phone: str | None = Field(default=None, max_length=32)
    vehicle_type: str | None = Field(default=None, max_length=50)
    allowed_gross_weight_tons: PositiveWeight
    remark: str | None = None

    _validate_plate = field_validator("plate_number")(_normalize_plate)


class VehicleUpdate(BaseModel):
    """Fields that may be changed on a vehicle master record."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    plate_number: str | None = Field(default=None, max_length=20)
    driver_name: str | None = Field(default=None, max_length=100)
    driver_phone: str | None = Field(default=None, max_length=32)
    vehicle_type: str | None = Field(default=None, max_length=50)
    allowed_gross_weight_tons: PositiveWeight | None = None
    remark: str | None = None

    @field_validator("plate_number")
    @classmethod
    def validate_optional_plate(cls, value: str | None) -> str | None:
        return None if value is None else _normalize_plate(value)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "VehicleUpdate":
        for field in ("plate_number", "allowed_gross_weight_tons"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class VehicleRead(BaseModel):
    """Vehicle representation returned by application boundaries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    plate_number: str
    driver_name: str | None
    driver_phone: str | None
    vehicle_type: str | None
    allowed_gross_weight_tons: Decimal
    remark: str | None
    created_at: datetime
    updated_at: datetime
