"""Import all models so Alembic can discover complete metadata."""

from app.models.audit_log import AuditLog
from app.models.billing import BillingRecord, BillingRule
from app.models.customer import Customer
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.weighing import WeighingRecord, WeighingTask
from app.models.weighing_reversal import WeighingReversal

__all__ = [
    "AuditLog",
    "BillingRecord",
    "BillingRule",
    "Customer",
    "Permission",
    "Role",
    "RolePermission",
    "User",
    "UserRole",
    "Vehicle",
    "WeighingRecord",
    "WeighingTask",
    "WeighingReversal",
]
