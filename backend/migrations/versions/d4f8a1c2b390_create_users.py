"""create users

Revision ID: d4f8a1c2b390
Revises: c7b9e2f4a610
Create Date: 2026-09-16 18:00:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d4f8a1c2b390"
down_revision: str | Sequence[str] | None = "c7b9e2f4a610"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the local user identity table without business-model relations."""
    op.create_table(
        "users",
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("real_name", sa.String(100), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    """Drop the local user identity table."""
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
