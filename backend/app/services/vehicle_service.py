"""Vehicle application service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.domain.exceptions import ConflictError, NotFoundError, VehicleHasHistoryError
from app.models.audit_log import AuditLog
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingTask
from app.schemas.lifecycle import DeleteEntityInput
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


class VehicleService:
    """Manage vehicle master data without exposing persistence details to APIs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_vehicle(self, data: VehicleCreate) -> Vehicle:
        existing = self._session.scalar(
            select(Vehicle).where(
                Vehicle.plate_number == data.plate_number,
                Vehicle.deleted_at.is_(None),
            )
        )
        if existing is not None:
            raise ConflictError(f"vehicle plate already exists: {data.plate_number}")

        vehicle = Vehicle(**data.model_dump())
        self._session.add(vehicle)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError(
                f"vehicle plate already exists: {data.plate_number}"
            ) from exc
        self._session.refresh(vehicle)
        return vehicle

    def get_vehicle(self, vehicle_id: UUID) -> Vehicle:
        vehicle = self._session.scalar(
            select(Vehicle).where(
                Vehicle.id == vehicle_id,
                Vehicle.deleted_at.is_(None),
            )
        )
        if vehicle is None:
            raise NotFoundError(f"vehicle not found: {vehicle_id}")
        return vehicle

    def list_vehicles(self) -> list[Vehicle]:
        """Return vehicles in a stable creation order for the V1 API."""
        return list(
            self._session.scalars(
                select(Vehicle)
                .where(Vehicle.deleted_at.is_(None))
                .order_by(Vehicle.created_at, Vehicle.id)
            )
        )

    def update_vehicle(self, vehicle_id: UUID, data: VehicleUpdate) -> Vehicle:
        vehicle = self.get_vehicle(vehicle_id)
        changes = data.model_dump(exclude_unset=True)

        new_plate = changes.get("plate_number")
        if new_plate is not None and new_plate != vehicle.plate_number:
            duplicate = self._session.scalar(
                select(Vehicle).where(
                    Vehicle.plate_number == new_plate,
                    Vehicle.id != vehicle_id,
                    Vehicle.deleted_at.is_(None),
                )
            )
            if duplicate is not None:
                raise ConflictError(f"vehicle plate already exists: {new_plate}")

        for field, value in changes.items():
            setattr(vehicle, field, value)

        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("vehicle update violates a unique constraint") from exc
        self._session.refresh(vehicle)
        return vehicle

    def delete_vehicle(self, vehicle_id: UUID, data: DeleteEntityInput) -> None:
        vehicle = self._session.scalar(
            select(Vehicle)
            .where(
                Vehicle.id == vehicle_id,
                Vehicle.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if vehicle is None:
            raise NotFoundError(f"vehicle not found: {vehicle_id}")
        history_count = self._session.scalar(
            select(func.count(WeighingTask.id)).where(
                WeighingTask.vehicle_id == vehicle_id
            )
        )
        if history_count:
            raise VehicleHasHistoryError("该车辆存在历史称重记录，无法删除")

        vehicle.deleted_at = utc_now()
        self._session.add(
            AuditLog(
                operator_id=data.operator_id,
                action="VEHICLE_DELETED",
                target_type="Vehicle",
                target_id=vehicle.id,
                before_value={"deleted_at": None},
                after_value={"deleted_at": vehicle.deleted_at.isoformat()},
                reason=data.reason,
            )
        )
        self._session.commit()
