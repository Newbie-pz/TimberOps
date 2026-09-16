"""Vehicle and snapshot business rules."""

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.domain.enums import CargoType, VehicleType
from app.domain.exceptions import ConflictError
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.schemas.weighing import WeighingTaskCreate
from app.services.vehicle_service import VehicleService
from app.services.weighing_service import WeighingService


def vehicle_data(
    *,
    plate_number: str = "蒙H12345",
    allowed: str = "49.000",
) -> VehicleCreate:
    return VehicleCreate(
        plate_number=plate_number,
        driver_name="张师傅",
        driver_phone="13800000000",
        vehicle_type=VehicleType.LARGE,
        allowed_gross_weight_tons=Decimal(allowed),
    )


def test_vehicle_weight_is_decimal_and_plate_is_normalized(
    db_session: Session,
) -> None:
    vehicle = VehicleService(db_session).create_vehicle(
        vehicle_data(plate_number="  蒙h12345 ")
    )

    assert vehicle.plate_number == "蒙H12345"
    assert vehicle.allowed_gross_weight_tons == Decimal("49.000")
    assert isinstance(vehicle.allowed_gross_weight_tons, Decimal)


def test_duplicate_plate_is_rejected(db_session: Session) -> None:
    service = VehicleService(db_session)
    service.create_vehicle(vehicle_data())

    with pytest.raises(ConflictError):
        service.create_vehicle(vehicle_data())


@pytest.mark.parametrize("value", ["0", "-0.001"])
def test_nonpositive_allowed_gross_is_rejected(value: str) -> None:
    with pytest.raises(PydanticValidationError):
        vehicle_data(allowed=value)


def test_task_keeps_allowed_weight_and_driver_snapshot(
    db_session: Session,
) -> None:
    vehicle_service = VehicleService(db_session)
    vehicle = vehicle_service.create_vehicle(vehicle_data())
    task = WeighingService(db_session).create_task(
        WeighingTaskCreate(vehicle_id=vehicle.id, cargo_type=CargoType.TIMBER)
    )

    vehicle_service.update_vehicle(
        vehicle.id,
        VehicleUpdate(
            allowed_gross_weight_tons=Decimal("48.000"),
            driver_name="新司机",
        ),
    )
    db_session.refresh(task)

    assert task.allowed_gross_weight_tons == Decimal("49.000")
    assert task.driver_name_snapshot == "张师傅"
    assert task.driver_phone_snapshot == "13800000000"


def test_weighing_service_exposes_no_vehicle_change_method() -> None:
    assert not hasattr(WeighingService, "update_vehicle")


@pytest.mark.parametrize(
    "payload",
    [{"plate_number": None}, {"allowed_gross_weight_tons": None}],
)
def test_vehicle_update_rejects_null_required_fields(
    payload: dict[str, None],
) -> None:
    with pytest.raises(PydanticValidationError):
        VehicleUpdate.model_validate(payload)
