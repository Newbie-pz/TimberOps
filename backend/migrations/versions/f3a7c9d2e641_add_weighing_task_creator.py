"""add weighing task creator identity

Revision ID: f3a7c9d2e641
Revises: e6a1b3c4d520
Create Date: 2026-09-16 22:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "f3a7c9d2e641"
down_revision: str | Sequence[str] | None = "e6a1b3c4d520"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store the authenticated creator while preserving historical nulls."""
    op.add_column("weighing_tasks", sa.Column("created_by", sa.Uuid()))
    op.create_foreign_key(
        "fk_weighing_tasks_created_by_users",
        "weighing_tasks",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_weighing_tasks_created_by",
        "weighing_tasks",
        ["created_by"],
    )


def downgrade() -> None:
    """Remove creator identity without touching historical task data."""
    op.drop_index("ix_weighing_tasks_created_by", table_name="weighing_tasks")
    op.drop_constraint(
        "fk_weighing_tasks_created_by_users",
        "weighing_tasks",
        type_="foreignkey",
    )
    op.drop_column("weighing_tasks", "created_by")
