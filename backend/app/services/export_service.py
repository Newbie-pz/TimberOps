"""Spreadsheet exports for operational weighing history."""

from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO
from uuid import UUID

from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import CargoType
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask


BUSINESS_TIMEZONE = timezone(timedelta(hours=8))


EXPORT_HEADERS = (
    "磅单编号",
    "时间",
    "车牌",
    "司机",
    "客户",
    "货物类型",
    "货物名称",
    "货物备注",
    "皮重(t)",
    "毛重(t)",
    "净重(t)",
    "状态",
    "结果",
)


class ExportService:
    """Query weighing rows and serialize them without changing business data."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def export_weighing(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        vehicle_id: UUID | None = None,
        customer_id: UUID | None = None,
        cargo_type: CargoType | None = None,
    ) -> bytes:
        """Return XLSX rows filtered by task creation date in UTC+08:00."""
        statement = (
            select(WeighingTask, Vehicle.plate_number, Customer.name)
            .join(Vehicle, Vehicle.id == WeighingTask.vehicle_id)
            .outerjoin(Customer, Customer.id == WeighingTask.customer_id)
        )
        if start_date is not None:
            statement = statement.where(
                WeighingTask.created_at >= self._day_start(start_date)
            )
        if end_date is not None:
            statement = statement.where(
                WeighingTask.created_at < self._day_start(end_date + timedelta(days=1))
            )
        if vehicle_id is not None:
            statement = statement.where(WeighingTask.vehicle_id == vehicle_id)
        if customer_id is not None:
            statement = statement.where(WeighingTask.customer_id == customer_id)
        if cargo_type is not None:
            statement = statement.where(WeighingTask.cargo_type == cargo_type)
        statement = statement.order_by(WeighingTask.created_at, WeighingTask.id)

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "称重历史"
        worksheet.append(EXPORT_HEADERS)
        for cell in worksheet[1]:
            cell.font = Font(bold=True)

        for task, plate_number, customer_name in self._session.execute(statement):
            worksheet.append(
                (
                    task.task_no,
                    self._excel_datetime(task.created_at),
                    plate_number,
                    task.driver_name_snapshot or "",
                    customer_name or "",
                    task.cargo_type.value,
                    task.cargo_name or "",
                    task.cargo_remark or "",
                    task.tare_weight_tons,
                    task.gross_weight_tons,
                    task.net_weight_tons,
                    task.status.value,
                    task.weight_result.value,
                )
            )

        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        worksheet.column_dimensions["A"].width = 30
        worksheet.column_dimensions["B"].width = 20
        for column in ("C", "D", "E", "F", "G", "H"):
            worksheet.column_dimensions[column].width = 18
        for column in ("I", "J", "K", "L", "M"):
            worksheet.column_dimensions[column].width = 14
        for row in worksheet.iter_rows(min_row=2, min_col=9, max_col=11):
            for cell in row:
                cell.number_format = "0.000"
        for cell in worksheet["B"][1:]:
            cell.number_format = "yyyy-mm-dd hh:mm:ss"

        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    @staticmethod
    def _day_start(value: date) -> datetime:
        return datetime.combine(value, time.min, tzinfo=BUSINESS_TIMEZONE).astimezone(
            timezone.utc
        )

    @staticmethod
    def _excel_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(BUSINESS_TIMEZONE).replace(tzinfo=None)
