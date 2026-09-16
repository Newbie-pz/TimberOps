"""Framework-independent application errors."""


class DomainError(Exception):
    """Base error for expected domain failures."""


class ValidationError(DomainError):
    """A command violates a business rule or state transition."""


class InvalidStateError(ValidationError):
    """A command is not legal in the entity's current lifecycle state."""


class BusinessRuleError(ValidationError):
    """A command conflicts with a non-state business invariant."""


class NotFoundError(DomainError):
    """A requested entity does not exist."""


class ConflictError(DomainError):
    """A command conflicts with an existing unique business value."""


class AuthenticationError(DomainError):
    """Credentials or bearer-token authentication failed."""


class CodedBusinessError(BusinessRuleError):
    """A business failure whose stable code is part of the public API contract."""

    code = "BUSINESS_CONFLICT"


class VehicleHasHistoryError(CodedBusinessError):
    """A vehicle with weighing history must remain addressable."""

    code = "VEHICLE_HAS_HISTORY"


class CustomerHasHistoryError(CodedBusinessError):
    """A customer with weighing history must remain addressable."""

    code = "CUSTOMER_HAS_HISTORY"
