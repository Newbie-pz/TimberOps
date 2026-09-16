"""Structured Agent tools backed exclusively by AnalyticsService."""

from collections.abc import Callable
from datetime import date
from typing import Any

from langchain_core.tools import BaseTool, tool
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.domain.enums import CargoType
from app.services.analytics_service import AnalyticsService


SessionFactory = Callable[[], Session]


def build_weighing_tools(
    session_factory: SessionFactory = SessionLocal,
) -> list[BaseTool]:
    """Build tools that each own and close an isolated database session."""

    @tool
    def get_today_weighing_summary() -> dict[str, Any]:
        """查询今天已完成任务的最终净重汇总及历史超重事件数量。"""
        with session_factory() as session:
            return AnalyticsService(session).get_today_weighing_summary()

    @tool
    def get_cargo_weight_summary(
        cargo_type: CargoType,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """查询指定货物和可选日期范围内已完成任务数及最终净货总重量。"""
        with session_factory() as session:
            return AnalyticsService(session).get_cargo_weight_summary(
                cargo_type=cargo_type,
                start_date=start_date,
                end_date=end_date,
            )

    @tool
    def get_overweight_records(
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """查询日期范围内曾经超重的任务，包含整改成功后仍保留的历史事件。"""
        with session_factory() as session:
            return AnalyticsService(session).get_overweight_records(
                start_date=start_date,
                end_date=end_date,
            )

    @tool
    def get_vehicle_weighing_history(
        plate_number: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """按完整车牌号查询车辆最近的称重任务，limit 范围为 1 至 100。"""
        with session_factory() as session:
            return AnalyticsService(session).get_vehicle_weighing_history(
                plate_number=plate_number,
                limit=limit,
            )

    @tool
    def get_weighing_task_detail(task_no: str) -> dict[str, Any]:
        """按完整任务编号查询任务业务摘要和按顺序排列的全部称重读数。"""
        with session_factory() as session:
            return AnalyticsService(session).get_weighing_task_detail(
                task_no=task_no
            )

    return [
        get_today_weighing_summary,
        get_cargo_weight_summary,
        get_overweight_records,
        get_vehicle_weighing_history,
        get_weighing_task_detail,
    ]
