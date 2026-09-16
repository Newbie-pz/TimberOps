"""Pydantic schemas for weighing commands and reads."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import (
    CargoType,
    WeighingDirection,
    WeighingStatus,
    WeightResult,
    WeightSource,
    WeightType,
)


PositiveWeight = Annotated[
    Decimal,
    Field(gt=0, max_digits=10, decimal_places=3),
]


class WeighingTaskCreate(BaseModel):
    """Client-controlled values for a new weighing task."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    vehicle_id: UUID
    customer_id: UUID | None = None
    weighing_direction: WeighingDirection = WeighingDirection.OUTBOUND
    cargo_type: CargoType
    cargo_name: str | None = Field(default=None, max_length=100)
    cargo_remark: str | None = None

class TareWeightInput(BaseModel):
    """Manual first tare reading."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    weight_tons: PositiveWeight
    remark: str | None = None


class GrossWeightInput(BaseModel):
    """Manual first gross reading."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    weight_tons: PositiveWeight
    remark: str | None = None


class ReweighInput(BaseModel):
    """Manual gross reweigh after an overweight result."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    weight_tons: PositiveWeight
    remark: str = Field(min_length=1)

    @field_validator("remark")
    @classmethod
    def validate_remark(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("remark is required for REWEIGH")
        return value


class CancelWeighingTaskInput(BaseModel):
    """Reason required to cancel an unfinished task."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason is required to cancel a task")
        return value


class WeighingRecordRead(BaseModel):
    """One immutable accepted scale reading."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    weighing_task_id: UUID
    weight_type: WeightType
    weight_tons: Decimal
    sequence_no: int
    recorded_at: datetime
    recorded_by: UUID | None
    source: WeightSource
    remark: str | None
    created_at: datetime


class WeighingTaskRead(BaseModel):
    """Current effective summary of a weighing task."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_no: str
    vehicle_id: UUID
    customer_id: UUID | None
    weighing_direction: WeighingDirection
    cargo_type: CargoType
    cargo_name: str | None
    cargo_remark: str | None
    driver_name_snapshot: str | None
    driver_phone_snapshot: str | None
    tare_weight_tons: Decimal | None
    gross_weight_tons: Decimal | None
    net_weight_tons: Decimal | None
    allowed_gross_weight_tons: Decimal
    overweight_tons: Decimal
    status: WeighingStatus
    weight_result: WeightResult
    tare_time: datetime | None
    gross_time: datetime | None
    completed_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class TaskDetailResponse(BaseModel):
    """Current task summary together with its ordered immutable history."""

    task: WeighingTaskRead
    records: list[WeighingRecordRead]
