"""Structured business-report response models."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import CargoType


ReportType = Literal["daily", "monthly"]


class ReportCargoRankingItem(BaseModel):
    cargo_type: CargoType
    completed_task_count: int
    total_net_weight_tons: Decimal


class ReportVehicleRankingItem(BaseModel):
    vehicle_id: UUID
    plate_number: str
    completed_task_count: int
    total_net_weight_tons: Decimal


class BusinessReport(BaseModel):
    """One closed-open UTC+8 reporting period rendered as inclusive dates."""

    report_type: ReportType
    period_start: date
    period_end: date
    timezone: Literal["UTC+08:00"] = "UTC+08:00"
    currency: Literal["CNY"] = "CNY"
    task_count: int
    completed_task_count: int
    completed_net_weight_tons: Decimal
    income: Decimal
    cargo_ranking: list[ReportCargoRankingItem]
    vehicle_ranking: list[ReportVehicleRankingItem]
