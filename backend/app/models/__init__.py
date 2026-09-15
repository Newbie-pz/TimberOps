"""Import all models so Alembic can discover complete metadata."""

from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingRecord, WeighingTask

__all__ = [
    "AuditLog",
    "Customer",
    "Vehicle",
    "WeighingRecord",
    "WeighingTask",
]
