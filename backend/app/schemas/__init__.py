"""Public Pydantic request and response schemas."""

from app.schemas.ai import AIChatRequest, AIChatResponse, AIToolCallRead
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.schemas.dashboard import DashboardOverview
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from app.schemas.weighing import (
    CancelWeighingTaskInput,
    GrossWeightInput,
    ReweighInput,
    TaskDetailResponse,
    TareWeightInput,
    WeighingRecordRead,
    WeighingTaskCreate,
    WeighingTaskRead,
)

__all__ = [
    "AIChatRequest",
    "AIChatResponse",
    "AIToolCallRead",
    "CancelWeighingTaskInput",
    "CustomerCreate",
    "CustomerRead",
    "CustomerUpdate",
    "DashboardOverview",
    "GrossWeightInput",
    "ReweighInput",
    "TaskDetailResponse",
    "TareWeightInput",
    "VehicleCreate",
    "VehicleRead",
    "VehicleUpdate",
    "WeighingRecordRead",
    "WeighingTaskCreate",
    "WeighingTaskRead",
]
