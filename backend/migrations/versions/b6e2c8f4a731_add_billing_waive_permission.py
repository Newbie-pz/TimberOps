"""add billing waiver permission and operator update grant

Revision ID: b6e2c8f4a731
Revises: a9c4e7b2d610
Create Date: 2026-09-17 14:00:00
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from alembic import op
import sqlalchemy as sa


revision: str = "b6e2c8f4a731"
down_revision: str | Sequence[str] | None = "a9c4e7b2d610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WAIVE_PERMISSION = "billing:waive"
OPERATOR_UPDATE_PERMISSION = "billing:update"


def _stable_id(kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"timberops:rbac:{kind}:{value}")


def upgrade() -> None:
    """Create the ADMIN-only waiver grant and enable OPERATOR payment updates."""
    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    role_permission_table = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_id", sa.Uuid()),
    )
    waive_permission_id = _stable_id("permission", WAIVE_PERMISSION)
    op.bulk_insert(
        permission_table,
        [
            {
                "id": waive_permission_id,
                "code": WAIVE_PERMISSION,
                "name": "免除费用",
                "description": "免除费用",
                "created_at": datetime.now(timezone.utc),
            }
        ],
    )
    grants = (
        ("ADMIN", WAIVE_PERMISSION, waive_permission_id),
        (
            "OPERATOR",
            OPERATOR_UPDATE_PERMISSION,
            _stable_id("permission", OPERATOR_UPDATE_PERMISSION),
        ),
    )
    op.bulk_insert(
        role_permission_table,
        [
            {
                "id": _stable_id("grant", f"{role_name}:{permission_code}"),
                "role_id": _stable_id("role", role_name),
                "permission_id": permission_id,
            }
            for role_name, permission_code, permission_id in grants
        ],
    )


def downgrade() -> None:
    """Remove Phase 2.6.2 grants and the waiver permission."""
    role_permission_table = sa.table(
        "role_permissions",
        sa.column("id", sa.Uuid()),
    )
    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
    )
    grant_ids = (
        _stable_id("grant", f"ADMIN:{WAIVE_PERMISSION}"),
        _stable_id("grant", f"OPERATOR:{OPERATOR_UPDATE_PERMISSION}"),
    )
    op.execute(
        role_permission_table.delete().where(
            role_permission_table.c.id.in_(grant_ids)
        )
    )
    op.execute(
        permission_table.delete().where(
            permission_table.c.id == _stable_id("permission", WAIVE_PERMISSION)
        )
    )
