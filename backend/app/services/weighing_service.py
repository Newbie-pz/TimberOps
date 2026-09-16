"""Transactional weighing state machine and append-only reading service."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.domain.enums import (
    CargoType,
    WeighingDirection,
    WeighingStatus,
    WeightResult,
    WeightSource,
    WeightType,
)
from app.domain.exceptions import (
    BusinessRuleError,
    ConflictError,
    InvalidStateError,
    NotFoundError,
)
from app.domain.weighing import calculate_weight, quantize_tons
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingRecord, WeighingTask
from app.schemas.weighing import (
    CancelWeighingTaskInput,
    GrossWeightInput,
    ReweighInput,
    TareWeightInput,
    WeighingTaskCreate,
)


class WeighingService:
    """Own all legal transitions and atomic task/reading updates."""

    _CANCELLABLE_STATUSES = frozenset(
        {
            WeighingStatus.WAIT_TARE,
            WeighingStatus.TARE_COMPLETED,
            WeighingStatus.WAIT_GROSS,
            WeighingStatus.GROSS_COMPLETED,
        }
    )

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_task(self, data: WeighingTaskCreate) -> WeighingTask:
        vehicle = self._session.get(Vehicle, data.vehicle_id)
        if vehicle is None:
            raise NotFoundError(f"vehicle not found: {data.vehicle_id}")
        if data.customer_id is not None:
            customer = self._session.get(Customer, data.customer_id)
            if customer is None:
                raise NotFoundError(f"customer not found: {data.customer_id}")
        if data.weighing_direction is not WeighingDirection.OUTBOUND:
            raise BusinessRuleError("V1 only supports OUTBOUND weighing")
        task = WeighingTask(
            task_no=self._new_task_no(),
            vehicle_id=vehicle.id,
            customer_id=data.customer_id,
            weighing_direction=data.weighing_direction,
            cargo_type=data.cargo_type,
            cargo_name=data.cargo_name,
            cargo_remark=data.cargo_remark,
            driver_name_snapshot=vehicle.driver_name,
            driver_phone_snapshot=vehicle.driver_phone,
            allowed_gross_weight_tons=quantize_tons(
                vehicle.allowed_gross_weight_tons
            ),
            overweight_tons=Decimal("0.000"),
            status=WeighingStatus.WAIT_TARE,
            weight_result=WeightResult.PENDING,
            version=1,
        )
        self._session.add(task)
        self._commit("could not create weighing task")
        self._session.refresh(task)
        return task

    def get_task(self, task_id: UUID) -> WeighingTask:
        """Return one task without changing its state."""
        task = self._session.get(WeighingTask, task_id)
        if task is None:
            raise NotFoundError(f"weighing task not found: {task_id}")
        return task

    def list_tasks(
        self,
        *,
        cargo_type: CargoType | None = None,
        status: WeighingStatus | None = None,
        vehicle_id: UUID | None = None,
    ) -> list[WeighingTask]:
        """List tasks using the simple filters supported by API V1."""
        statement = select(WeighingTask)
        if cargo_type is not None:
            statement = statement.where(WeighingTask.cargo_type == cargo_type)
        if status is not None:
            statement = statement.where(WeighingTask.status == status)
        if vehicle_id is not None:
            statement = statement.where(WeighingTask.vehicle_id == vehicle_id)
        statement = statement.order_by(WeighingTask.created_at, WeighingTask.id)
        return list(self._session.scalars(statement))

    def list_records(self, task_id: UUID) -> list[WeighingRecord]:
        """Return all accepted readings in immutable sequence order."""
        self.get_task(task_id)
        return list(
            self._session.scalars(
                select(WeighingRecord)
                .where(WeighingRecord.weighing_task_id == task_id)
                .order_by(WeighingRecord.sequence_no)
            )
        )

    def record_tare(
        self,
        task_id: UUID,
        data: TareWeightInput,
        *,
        operator_id: UUID | None = None,
    ) -> WeighingTask:
        task = self._get_task_for_update(task_id)
        self._require_status(task, WeighingStatus.WAIT_TARE)
        now = utc_now()
        weight = quantize_tons(data.weight_tons)
        self._append_record(
            task=task,
            weight_type=WeightType.TARE,
            weight_tons=weight,
            recorded_at=now,
            recorded_by=operator_id,
            remark=data.remark,
        )
        task.tare_weight_tons = weight
        task.tare_time = now
        task.status = WeighingStatus.TARE_COMPLETED
        task.version += 1
        self._commit("could not record tare weight")
        return task

    def start_loading(self, task_id: UUID) -> WeighingTask:
        """Compatibility alias: the removed LOADING state now means WAIT_GROSS."""
        return self.prepare_for_gross(task_id)

    def finish_loading(self, task_id: UUID) -> WeighingTask:
        """Compatibility alias retained for existing `/wait-gross` clients."""
        return self.prepare_for_gross(task_id)

    def prepare_for_gross(self, task_id: UUID) -> WeighingTask:
        """Move directly from completed tare weighing to gross weighing."""
        task = self._get_task_for_update(task_id)
        if task.status is WeighingStatus.WAIT_GROSS:
            return task
        self._require_status(task, WeighingStatus.TARE_COMPLETED)
        task.status = WeighingStatus.WAIT_GROSS
        task.version += 1
        self._commit("could not prepare gross weighing")
        return task

    def record_gross(
        self,
        task_id: UUID,
        data: GrossWeightInput,
        *,
        operator_id: UUID | None = None,
    ) -> WeighingTask:
        task = self._get_task_for_update(task_id)
        self._require_status(task, WeighingStatus.WAIT_GROSS)
        if task.weight_result is not WeightResult.PENDING or self._has_gross_record(task):
            raise InvalidStateError(
                "use record_reweigh after the first gross reading"
            )
        return self._record_gross_like(
            task=task,
            weight_type=WeightType.GROSS,
            weight_tons=data.weight_tons,
            operator_id=operator_id,
            remark=data.remark,
        )

    def record_reweigh(
        self,
        task_id: UUID,
        data: ReweighInput,
        *,
        operator_id: UUID | None = None,
    ) -> WeighingTask:
        task = self._get_task_for_update(task_id)
        self._require_status(task, WeighingStatus.WAIT_GROSS)
        if task.weight_result is not WeightResult.OVERWEIGHT:
            raise BusinessRuleError(
                "REWEIGH is only allowed after an overweight result"
            )
        if not data.remark.strip():
            raise BusinessRuleError("remark is required for REWEIGH")
        return self._record_gross_like(
            task=task,
            weight_type=WeightType.REWEIGH,
            weight_tons=data.weight_tons,
            operator_id=operator_id,
            remark=data.remark,
        )

    def complete_task(self, task_id: UUID) -> WeighingTask:
        task = self._get_task_for_update(task_id)
        if task.weight_result is not WeightResult.NORMAL:
            raise BusinessRuleError("only a NORMAL weighing task can be completed")
        self._require_status(task, WeighingStatus.GROSS_COMPLETED)
        task.status = WeighingStatus.COMPLETED
        task.completed_at = utc_now()
        task.version += 1
        self._commit("could not complete weighing task")
        return task

    def cancel_task(
        self,
        task_id: UUID,
        data: CancelWeighingTaskInput,
        *,
        operator_id: UUID | None = None,
    ) -> WeighingTask:
        task = self._get_task_for_update(task_id)
        if task.status not in self._CANCELLABLE_STATUSES:
            raise InvalidStateError(
                f"task in {task.status.value} cannot be cancelled"
            )

        previous_status = task.status
        task.status = WeighingStatus.CANCELLED
        task.version += 1
        self._session.add(
            AuditLog(
                operator_id=operator_id,
                action="WEIGHING_TASK_CANCELLED",
                target_type="WeighingTask",
                target_id=task.id,
                before_value={"status": previous_status.value},
                after_value={"status": WeighingStatus.CANCELLED.value},
                reason=data.reason,
            )
        )
        self._commit("could not cancel weighing task")
        return task

    def _record_gross_like(
        self,
        *,
        task: WeighingTask,
        weight_type: WeightType,
        weight_tons: Decimal,
        operator_id: UUID | None,
        remark: str | None,
    ) -> WeighingTask:
        if task.tare_weight_tons is None:
            raise InvalidStateError(
                "tare weight must exist before gross weighing"
            )

        calculation = calculate_weight(
            tare_weight_tons=task.tare_weight_tons,
            gross_weight_tons=weight_tons,
            allowed_gross_weight_tons=task.allowed_gross_weight_tons,
        )
        now = utc_now()
        self._append_record(
            task=task,
            weight_type=weight_type,
            weight_tons=calculation.gross_weight_tons,
            recorded_at=now,
            recorded_by=operator_id,
            remark=remark,
        )
        task.gross_weight_tons = calculation.gross_weight_tons
        task.net_weight_tons = calculation.net_weight_tons
        task.overweight_tons = calculation.overweight_tons
        task.weight_result = calculation.result
        task.gross_time = now
        task.status = (
            WeighingStatus.GROSS_COMPLETED
            if calculation.result is WeightResult.NORMAL
            else WeighingStatus.WAIT_GROSS
        )
        task.version += 1
        self._commit("could not record gross weight")
        return task

    def _get_task_for_update(self, task_id: UUID) -> WeighingTask:
        task = self._session.scalar(
            select(WeighingTask)
            .where(WeighingTask.id == task_id)
            .with_for_update()
        )
        if task is None:
            raise NotFoundError(f"weighing task not found: {task_id}")
        return task

    def _append_record(
        self,
        *,
        task: WeighingTask,
        weight_type: WeightType,
        weight_tons: Decimal,
        recorded_at: datetime,
        recorded_by: UUID | None,
        remark: str | None,
    ) -> None:
        sequence_no = self._session.scalar(
            select(func.coalesce(func.max(WeighingRecord.sequence_no), 0) + 1).where(
                WeighingRecord.weighing_task_id == task.id
            )
        )
        self._session.add(
            WeighingRecord(
                weighing_task_id=task.id,
                weight_type=weight_type,
                weight_tons=weight_tons,
                sequence_no=int(sequence_no or 1),
                recorded_at=recorded_at,
                recorded_by=recorded_by,
                source=WeightSource.MANUAL,
                remark=remark,
            )
        )

    def _has_gross_record(self, task: WeighingTask) -> bool:
        count = self._session.scalar(
            select(func.count(WeighingRecord.id)).where(
                WeighingRecord.weighing_task_id == task.id,
                WeighingRecord.weight_type.in_(
                    [WeightType.GROSS, WeightType.REWEIGH]
                ),
            )
        )
        return bool(count)

    @staticmethod
    def _require_status(task: WeighingTask, expected: WeighingStatus) -> None:
        if task.status is not expected:
            raise InvalidStateError(
                f"task in {task.status.value} cannot perform an action requiring "
                f"{expected.value}"
            )

    def _commit(self, message: str) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError(message) from exc
        except Exception:
            self._session.rollback()
            raise

    @staticmethod
    def _new_task_no() -> str:
        timestamp = utc_now().strftime("%Y%m%d%H%M%S")
        return f"WT-{timestamp}-{uuid4().hex[:10].upper()}"
