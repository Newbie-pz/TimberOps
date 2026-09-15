"""Pure weighing calculation tests."""

from decimal import Decimal

import pytest

from app.domain.enums import WeightResult
from app.domain.exceptions import ValidationError
from app.domain.weighing import calculate_weight


def test_normal_weight_calculation() -> None:
    result = calculate_weight(
        tare_weight_tons=Decimal("15.820"),
        gross_weight_tons=Decimal("47.360"),
        allowed_gross_weight_tons=Decimal("49.000"),
    )

    assert result.net_weight_tons == Decimal("31.540")
    assert result.overweight_tons == Decimal("0.000")
    assert result.result is WeightResult.NORMAL


def test_overweight_calculation() -> None:
    result = calculate_weight(
        tare_weight_tons=Decimal("15.820"),
        gross_weight_tons=Decimal("50.200"),
        allowed_gross_weight_tons=Decimal("49.000"),
    )

    assert result.net_weight_tons == Decimal("34.380")
    assert result.overweight_tons == Decimal("1.200")
    assert result.result is WeightResult.OVERWEIGHT


@pytest.mark.parametrize("gross", ["15.820", "15.000"])
def test_gross_not_above_tare_is_rejected(gross: str) -> None:
    with pytest.raises(ValidationError, match="greater than tare"):
        calculate_weight(
            tare_weight_tons=Decimal("15.820"),
            gross_weight_tons=Decimal(gross),
            allowed_gross_weight_tons=Decimal("49.000"),
        )
