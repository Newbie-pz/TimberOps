"""add completed weighing reversal workflow

Revision ID: e4b7a2c9d631
Revises: d8a3f6c1b954
Create Date: 2026-10-11 12:00:00
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from alembic import op
import sqlalchemy as sa

revision: str = "e4b7a2c9d631"
down_revision: str | Sequence[str] | None = "d8a3f6c1b954"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _stable_id(kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"timberops:rbac:{kind}:{value}")


def upgrade() -> None:
    """Add immutable reversals and grant the high-risk action to ADMIN only."""
    op.create_table(
        "weighing_reversals",
        sa.Column("original_task_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("billing_record_id", sa.Uuid(), nullable=True),
        sa.Column("billing_payment_status_snapshot", sa.String(6), nullable=True),
        sa.Column("billing_fee_amount_snapshot", sa.Numeric(10, 2), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="ck_weighing_reversals_reason_not_blank",
        ),
        sa.CheckConstraint(
            "billing_payment_status_snapshot IS NULL OR "
            "billing_payment_status_snapshot IN ('UNPAID', 'PAID', 'WAIVED')",
            name="reversal_billing_payment_status",
        ),
        sa.ForeignKeyConstraint(
            ["original_task_id"], ["weighing_tasks.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["billing_record_id"], ["billing_records.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "original_task_id", name="uq_weighing_reversals_original_task"
        ),
    )
    op.create_index(
        "ix_weighing_reversals_original_task_id",
        "weighing_reversals",
        ["original_task_id"],
    )
    op.create_index(
        "ix_weighing_reversals_created_by",
        "weighing_reversals",
        ["created_by"],
    )

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
    code = "weighing:reverse"
    op.bulk_insert(
        permission_table,
        [{
            "id": _stable_id("permission", code),
            "code": code,
            "name": "冲正已完成称重任务",
            "description": "冲正已完成称重任务",
            "created_at": datetime.now(timezone.utc),
        }],
    )
    op.bulk_insert(
        role_permission_table,
        [{
            "id": _stable_id("grant", f"ADMIN:{code}"),
            "role_id": _stable_id("role", "ADMIN"),
            "permission_id": _stable_id("permission", code),
        }],
    )


def downgrade() -> None:
    """Remove the ADMIN grant, permission, and reversal records."""
    permission_id = _stable_id("permission", "weighing:reverse")
    role_permission_table = sa.table(
        "role_permissions", sa.column("permission_id", sa.Uuid())
    )
    permission_table = sa.table("permissions", sa.column("id", sa.Uuid()))
    op.execute(
        role_permission_table.delete().where(
            role_permission_table.c.permission_id == permission_id
        )
    )
    op.execute(permission_table.delete().where(permission_table.c.id == permission_id))
    op.drop_index(
        "ix_weighing_reversals_created_by", table_name="weighing_reversals"
    )
    op.drop_index(
        "ix_weighing_reversals_original_task_id", table_name="weighing_reversals"
    )
    op.drop_table("weighing_reversals")
