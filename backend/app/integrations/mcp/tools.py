"""MCP tool adapters; all business queries remain in AnalyticsService."""

from collections.abc import Callable
from datetime import date
from typing import Annotated

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field
from sqlalchemy.orm import Session

from app.domain.enums import CargoType
from app.integrations.mcp.schemas import (
    CargoWeightSummary,
    OverweightRecord,
    OverweightRecords,
    TodayWeighingSummary,
    VehicleWeighingHistory,
    WeighingTaskDetail,
)
from app.services.analytics_service import AnalyticsService


SessionFactory = Callable[[], Session]
READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    openWorldHint=False,
)


def register_analytics_tools(
    server: MCPServer,
    session_factory: SessionFactory,
) -> None:
    """Register the five existing query capabilities as read-only MCP tools."""

    @server.tool(annotations=READ_ONLY_ANNOTATIONS, structured_output=True)
    def get_today_weighing_summary() -> TodayWeighingSummary:
        """查询今天已完成任务的最终净重汇总及历史超重事件数量。"""
        with session_factory() as session:
            result = AnalyticsService(session).get_today_weighing_summary()
        return TodayWeighingSummary.model_validate(result)

    @server.tool(annotations=READ_ONLY_ANNOTATIONS, structured_output=True)
    def get_cargo_weight_summary(
        cargo_type: CargoType,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CargoWeightSummary:
        """查询指定货物和日期范围内已完成任务数及最终净货总重量。"""
        with session_factory() as session:
            result = AnalyticsService(session).get_cargo_weight_summary(
                cargo_type=cargo_type,
                start_date=start_date,
                end_date=end_date,
            )
        return CargoWeightSummary.model_validate(result)

    @server.tool(annotations=READ_ONLY_ANNOTATIONS, structured_output=True)
    def get_overweight_records(
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> OverweightRecords:
        """查询历史超重事件，包括复磅后最终恢复正常的任务。"""
        with session_factory() as session:
            result = AnalyticsService(session).get_overweight_records(
                start_date=start_date,
                end_date=end_date,
            )
        return OverweightRecords(
            records=[OverweightRecord.model_validate(item) for item in result]
        )

    @server.tool(annotations=READ_ONLY_ANNOTATIONS, structured_output=True)
    def get_vehicle_weighing_history(
        plate_number: str,
        limit: Annotated[int, Field(ge=1, le=100)] = 10,
    ) -> VehicleWeighingHistory:
        """按完整车牌号查询车辆最近的称重任务。"""
        with session_factory() as session:
            result = AnalyticsService(session).get_vehicle_weighing_history(
                plate_number=plate_number,
                limit=limit,
            )
        return VehicleWeighingHistory.model_validate(result)

    @server.tool(annotations=READ_ONLY_ANNOTATIONS, structured_output=True)
    def get_weighing_task_detail(task_no: str) -> WeighingTaskDetail:
        """按完整任务编号查询任务业务摘要及不可变称重历史。"""
        with session_factory() as session:
            result = AnalyticsService(session).get_weighing_task_detail(
                task_no=task_no
            )
        return WeighingTaskDetail.model_validate(result)
