"""simplify weighing and allow optional cargo name

Revision ID: 8f4b2c1d9a70
Revises: 2e11a7a8e890
Create Date: 2026-09-16 10:00:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "8f4b2c1d9a70"
down_revision: str | Sequence[str] | None = "2e11a7a8e890"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Collapse active LOADING tasks and relax the optional cargo name."""
    op.execute(
        "UPDATE weighing_tasks SET status = 'WAIT_GROSS' "
        "WHERE status = 'LOADING'"
    )
    op.drop_constraint("weighing_status", "weighing_tasks", type_="check")
    op.create_check_constraint(
        "weighing_status",
        "weighing_tasks",
        "status IN ('WAIT_TARE', 'TARE_COMPLETED', 'WAIT_GROSS', "
        "'GROSS_COMPLETED', 'COMPLETED', 'CANCELLED')",
    )
    op.drop_constraint(
        "ck_weighing_tasks_other_has_cargo_name",
        "weighing_tasks",
        type_="check",
    )


def downgrade() -> None:
    """Restore former constraints, filling names required by the old schema."""
    op.execute(
        "UPDATE weighing_tasks SET cargo_name = '其他' "
        "WHERE cargo_type = 'OTHER' "
        "AND (cargo_name IS NULL OR length(trim(cargo_name)) = 0)"
    )
    op.create_check_constraint(
        "ck_weighing_tasks_other_has_cargo_name",
        "weighing_tasks",
        "cargo_type != 'OTHER' OR "
        "(cargo_name IS NOT NULL AND length(trim(cargo_name)) > 0)",
    )
    op.drop_constraint("weighing_status", "weighing_tasks", type_="check")
    op.create_check_constraint(
        "weighing_status",
        "weighing_tasks",
        "status IN ('WAIT_TARE', 'TARE_COMPLETED', 'LOADING', 'WAIT_GROSS', "
        "'GROSS_COMPLETED', 'COMPLETED', 'CANCELLED')",
    )
