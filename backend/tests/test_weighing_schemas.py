"""Boundary validation for weighing commands."""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.domain.enums import CargoType
from app.schemas.weighing import ReweighInput, WeighingTaskCreate


def test_other_cargo_allows_empty_name() -> None:
    data = WeighingTaskCreate(vehicle_id=uuid4(), cargo_type=CargoType.OTHER)

    assert data.cargo_name is None


def test_other_cargo_accepts_specific_name() -> None:
    data = WeighingTaskCreate(
        vehicle_id=uuid4(),
        cargo_type=CargoType.OTHER,
        cargo_name="石料",
    )
    assert data.cargo_name == "石料"


def test_reweigh_requires_nonblank_remark() -> None:
    with pytest.raises(PydanticValidationError):
        ReweighInput(weight_tons=Decimal("48.600"), remark="   ")


def test_system_managed_fields_are_rejected() -> None:
    with pytest.raises(PydanticValidationError):
        WeighingTaskCreate.model_validate(
            {
                "vehicle_id": uuid4(),
                "cargo_type": "TIMBER",
                "status": "COMPLETED",
            }
        )
