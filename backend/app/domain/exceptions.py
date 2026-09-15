"""Framework-independent application errors."""


class DomainError(Exception):
    """Base error for expected domain failures."""


class ValidationError(DomainError):
    """A command violates a business rule or state transition."""


class NotFoundError(DomainError):
    """A requested entity does not exist."""


class ConflictError(DomainError):
    """A command conflicts with an existing unique business value."""
