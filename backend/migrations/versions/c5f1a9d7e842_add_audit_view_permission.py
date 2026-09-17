"""add audit view permission

Revision ID: c5f1a9d7e842
Revises: b6e2c8f4a731
Create Date: 2026-09-17 16:00:00
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from alembic import op
import sqlalchemy as sa


revision: str = "c5f1a9d7e842"
down_revision: str | Sequence[str] | None = "b6e2c8f4a731"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION_CODE = "audit:view"
ROLE_NAMES = ("ADMIN", "OPERATOR")


def _stable_id(kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"timberops:rbac:{kind}:{value}")


def upgrade() -> None:
    """Grant audit-trail visibility to administrators and operators."""
    permission_id = _stable_id("permission", PERMISSION_CODE)
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
    op.bulk_insert(
        permission_table,
        [
            {
                "id": permission_id,
                "code": PERMISSION_CODE,
                "name": "查看审计日志",
                "description": "查看审计日志",
                "created_at": datetime.now(timezone.utc),
            }
        ],
    )
    op.bulk_insert(
        role_permission_table,
        [
            {
                "id": _stable_id("grant", f"{role_name}:{PERMISSION_CODE}"),
                "role_id": _stable_id("role", role_name),
                "permission_id": permission_id,
            }
            for role_name in ROLE_NAMES
        ],
    )


def downgrade() -> None:
    """Remove audit visibility grants and their permission catalog entry."""
    permission_id = _stable_id("permission", PERMISSION_CODE)
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
            role_permission_table.c.permission_id == permission_id
        )
    )
    op.execute(
        permission_table.delete().where(permission_table.c.id == permission_id)
    )
