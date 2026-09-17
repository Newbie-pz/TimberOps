"""add business report permissions

Revision ID: d8a3f6c1b954
Revises: c5f1a9d7e842
Create Date: 2026-09-17 18:00:00
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from alembic import op
import sqlalchemy as sa


revision: str = "d8a3f6c1b954"
down_revision: str | Sequence[str] | None = "c5f1a9d7e842"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = (
    ("report:view", "查看业务报表"),
    ("report:export", "导出业务报表"),
)
GRANTS = {
    "ADMIN": ("report:view", "report:export"),
    "OPERATOR": ("report:view", "report:export"),
    "VIEWER": ("report:view",),
}


def _stable_id(kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"timberops:rbac:{kind}:{value}")


def upgrade() -> None:
    """Seed report view/export capabilities for the built-in role matrix."""
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
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        permission_table,
        [
            {
                "id": _stable_id("permission", code),
                "code": code,
                "name": name,
                "description": name,
                "created_at": now,
            }
            for code, name in PERMISSIONS
        ],
    )
    op.bulk_insert(
        role_permission_table,
        [
            {
                "id": _stable_id("grant", f"{role_name}:{permission_code}"),
                "role_id": _stable_id("role", role_name),
                "permission_id": _stable_id("permission", permission_code),
            }
            for role_name, permission_codes in GRANTS.items()
            for permission_code in permission_codes
        ],
    )


def downgrade() -> None:
    """Remove report grants and their permission catalog entries."""
    permission_ids = tuple(
        _stable_id("permission", code) for code, _ in PERMISSIONS
    )
    role_permission_table = sa.table(
        "role_permissions",
        sa.column("permission_id", sa.Uuid()),
    )
    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
    )
    op.execute(
        role_permission_table.delete().where(
            role_permission_table.c.permission_id.in_(permission_ids)
        )
    )
    op.execute(
        permission_table.delete().where(
            permission_table.c.id.in_(permission_ids)
        )
    )
