"""Pure Decimal-based weighing calculations."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.domain.enums import WeightResult
from app.domain.exceptions import ValidationError


TON_QUANTUM = Decimal("0.001")
ZERO_TONS = Decimal("0.000")


def quantize_tons(value: Decimal) -> Decimal:
    """Normalize a weight to the platform's 0.001 t precision."""
    return value.quantize(TON_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class WeightCalculation:
    """Calculated current summary for a gross or reweigh reading."""

    gross_weight_tons: Decimal
    net_weight_tons: Decimal
    overweight_tons: Decimal
    result: WeightResult


def calculate_weight(
    *,
    tare_weight_tons: Decimal,
    gross_weight_tons: Decimal,
    allowed_gross_weight_tons: Decimal,
) -> WeightCalculation:
    """Calculate net weight and overload without binary floating-point math."""
    tare = quantize_tons(tare_weight_tons)
    gross = quantize_tons(gross_weight_tons)
    allowed = quantize_tons(allowed_gross_weight_tons)

    if tare <= ZERO_TONS:
        raise ValidationError("tare weight must be greater than zero")
    if allowed <= ZERO_TONS:
        raise ValidationError("allowed gross weight must be greater than zero")
    if gross <= tare:
        raise ValidationError("gross weight must be greater than tare weight")

    net = quantize_tons(gross - tare)
    overweight = quantize_tons(max(gross - allowed, ZERO_TONS))
    result = (
        WeightResult.NORMAL
        if gross <= allowed
        else WeightResult.OVERWEIGHT
    )
    return WeightCalculation(
        gross_weight_tons=gross,
        net_weight_tons=net,
        overweight_tons=overweight,
        result=result,
    )
