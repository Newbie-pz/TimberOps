"""Vehicle application service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.exceptions import ConflictError, NotFoundError
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


class VehicleService:
    """Manage vehicle master data without exposing persistence details to APIs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_vehicle(self, data: VehicleCreate) -> Vehicle:
        existing = self._session.scalar(
            select(Vehicle).where(Vehicle.plate_number == data.plate_number)
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
        vehicle = self._session.get(Vehicle, vehicle_id)
        if vehicle is None:
            raise NotFoundError(f"vehicle not found: {vehicle_id}")
        return vehicle

    def list_vehicles(self) -> list[Vehicle]:
        """Return vehicles in a stable creation order for the V1 API."""
        return list(
            self._session.scalars(
                select(Vehicle).order_by(Vehicle.created_at, Vehicle.id)
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
