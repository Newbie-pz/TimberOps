"""Strong output contracts advertised by TimberOps MCP tools."""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    CargoType,
    WeighingStatus,
    WeightResult,
    WeightSource,
    WeightType,
)


class MCPOutputModel(BaseModel):
    """Reject accidental output drift from AnalyticsService contracts."""

    model_config = ConfigDict(extra="forbid")


class TodayWeighingSummary(MCPOutputModel):
    date: str
    completed_tasks: int
    total_net_weight_tons: str
    coal_weight_tons: str
    ore_weight_tons: str
    timber_weight_tons: str
    overweight_events: int


class CargoWeightSummary(MCPOutputModel):
    cargo_type: CargoType
    start_date: str | None
    end_date: str | None
    completed_tasks: int
    total_net_weight_tons: str


class OverweightRecord(MCPOutputModel):
    plate_number: str
    task_no: str
    cargo_type: CargoType
    first_overweight_weight_tons: str
    allowed_gross_weight_tons: str
    overweight_tons: str
    event_time: str | None
    final_status: WeighingStatus
    final_weight_result: WeightResult
    finally_completed: bool


class OverweightRecords(MCPOutputModel):
    records: list[OverweightRecord]


class VehicleWeighingTask(MCPOutputModel):
    task_no: str
    cargo_type: CargoType
    final_net_weight_tons: str | None
    status: WeighingStatus
    weight_result: WeightResult
    time: str | None


class VehicleWeighingHistory(MCPOutputModel):
    plate_number: str
    tasks: list[VehicleWeighingTask]


class WeighingRecordSummary(MCPOutputModel):
    sequence_no: int
    weight_type: WeightType
    weight_tons: str
    recorded_at: str | None
    source: WeightSource
    remark: str | None


class WeighingTaskDetail(MCPOutputModel):
    found: bool
    task_no: str
    plate_number: str | None = None
    customer_name: str | None = None
    cargo_type: CargoType | None = None
    cargo_name: str | None = None
    cargo_remark: str | None = None
    driver_name: str | None = None
    tare_weight_tons: str | None = None
    gross_weight_tons: str | None = None
    net_weight_tons: str | None = None
    allowed_gross_weight_tons: str | None = None
    overweight_tons: str | None = None
    status: WeighingStatus | None = None
    weight_result: WeightResult | None = None
    created_at: str | None = None
    completed_at: str | None = None
    records: list[WeighingRecordSummary] = Field(default_factory=list)
