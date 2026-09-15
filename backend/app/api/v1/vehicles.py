"""Vehicle REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate
from app.services.vehicle_service import VehicleService


router = APIRouter(prefix="/vehicles", tags=["vehicles"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(data: VehicleCreate, session: DbSession) -> object:
    return VehicleService(session).create_vehicle(data)


@router.get("", response_model=list[VehicleRead])
def list_vehicles(session: DbSession) -> object:
    return VehicleService(session).list_vehicles()


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle(vehicle_id: UUID, session: DbSession) -> object:
    return VehicleService(session).get_vehicle(vehicle_id)


@router.patch("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(
    vehicle_id: UUID,
    data: VehicleUpdate,
    session: DbSession,
) -> object:
    return VehicleService(session).update_vehicle(vehicle_id, data)
