"""Public Pydantic request and response schemas."""

from app.schemas.ai import AIChatRequest, AIChatResponse, AIToolCallRead
from app.schemas.auth import RegistrationStatusResponse
from app.schemas.audit import AuditLogRead
from app.schemas.billing import BillingRecordListItem, BillingRecordRead
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.schemas.dashboard import DashboardOverview
from app.schemas.report import BusinessReport
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
    "AuditLogRead",
    "BillingRecordListItem",
    "BillingRecordRead",
    "CancelWeighingTaskInput",
    "CustomerCreate",
    "CustomerRead",
    "CustomerUpdate",
    "DashboardOverview",
    "BusinessReport",
    "GrossWeightInput",
    "ReweighInput",
    "RegistrationStatusResponse",
    "TaskDetailResponse",
    "TareWeightInput",
    "VehicleCreate",
    "VehicleRead",
    "VehicleUpdate",
    "WeighingRecordRead",
    "WeighingTaskCreate",
    "WeighingTaskRead",
]
