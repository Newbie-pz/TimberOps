"""Read models for the operations dashboard."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums import CargoType, WeighingStatus


class StatusDistributionItem(BaseModel):
    """Current number of non-deleted tasks in one lifecycle state."""

    status: WeighingStatus
    count: int


class CargoWeightRankingItem(BaseModel):
    """Completed cargo volume for the current UTC+8 business day."""

    cargo_type: CargoType
    completed_task_count: int
    total_net_weight_tons: Decimal


class VehicleTransportRankingItem(BaseModel):
    """All-time completed transport volume for a vehicle."""

    vehicle_id: UUID
    plate_number: str
    completed_task_count: int
    total_net_weight_tons: Decimal


class DashboardOverview(BaseModel):
    """Stable, structured payload consumed by the operations dashboard."""

    business_date: date
    timezone: Literal["UTC+08:00"] = "UTC+08:00"
    currency: Literal["CNY"] = "CNY"
    today_task_count: int
    today_completed_task_count: int
    pending_task_count: int
    today_completed_net_weight_tons: Decimal
    today_income: Decimal
    status_distribution: list[StatusDistributionItem]
    cargo_weight_ranking: list[CargoWeightRankingItem]
    vehicle_transport_ranking: list[VehicleTransportRankingItem]
