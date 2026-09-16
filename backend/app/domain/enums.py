"""String enums persisted as portable VARCHAR values."""

from enum import StrEnum


class CargoType(StrEnum):
    """Cargo categories supported by weighing V1."""

    ORE = "ORE"
    COAL = "COAL"
    TIMBER = "TIMBER"
    OTHER = "OTHER"


class VehicleType(StrEnum):
    """Standard vehicle classes used by operations and billing."""

    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class PaymentStatus(StrEnum):
    """Billing state; external payment processing is intentionally out of scope."""

    UNPAID = "UNPAID"
    PAID = "PAID"
    WAIVED = "WAIVED"


class WeighingStatus(StrEnum):
    """Lifecycle state of a weighing task."""

    WAIT_TARE = "WAIT_TARE"
    TARE_COMPLETED = "TARE_COMPLETED"
    WAIT_GROSS = "WAIT_GROSS"
    GROSS_COMPLETED = "GROSS_COMPLETED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WeightResult(StrEnum):
    """Latest gross-weight evaluation, separate from task lifecycle."""

    PENDING = "PENDING"
    NORMAL = "NORMAL"
    OVERWEIGHT = "OVERWEIGHT"


class WeightType(StrEnum):
    """Meaning of an immutable scale reading."""

    TARE = "TARE"
    GROSS = "GROSS"
    REWEIGH = "REWEIGH"


class WeightSource(StrEnum):
    """Origin of a scale reading."""

    MANUAL = "MANUAL"
    DEVICE = "DEVICE"


class WeighingDirection(StrEnum):
    """Vehicle movement direction; V1 implements OUTBOUND only."""

    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"
