"""add lifecycle, standardized vehicle types, and billing

Revision ID: c7b9e2f4a610
Revises: 8f4b2c1d9a70
Create Date: 2026-09-16 16:00:00
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from alembic import op
import sqlalchemy as sa


revision: str = "c7b9e2f4a610"
down_revision: str | Sequence[str] | None = "8f4b2c1d9a70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add soft deletion and billing without discarding legacy vehicle types."""
    op.add_column("vehicles", sa.Column("vehicle_type_legacy", sa.String(50)))
    op.add_column(
        "vehicles", sa.Column("deleted_at", sa.DateTime(timezone=True))
    )
    op.create_index("ix_vehicles_deleted_at", "vehicles", ["deleted_at"])

    # Known labels are normalized. Unknown historical input remains recoverable.
    op.execute(
        "UPDATE vehicles SET vehicle_type_legacy = vehicle_type "
        "WHERE vehicle_type IS NOT NULL AND vehicle_type NOT IN ("
        "'SMALL', 'MEDIUM', 'LARGE', '小型货车', '小型', "
        "'中型货车', '中型', '大型货车', '大型', '重型货车', '重型')"
    )
    op.execute(
        "UPDATE vehicles SET vehicle_type = CASE "
        "WHEN vehicle_type IN ('SMALL', '小型货车', '小型') THEN 'SMALL' "
        "WHEN vehicle_type IN ('MEDIUM', '中型货车', '中型') THEN 'MEDIUM' "
        "WHEN vehicle_type IN ('LARGE', '大型货车', '大型', '重型货车', '重型') "
        "THEN 'LARGE' ELSE NULL END"
    )
    op.alter_column(
        "vehicles",
        "vehicle_type",
        existing_type=sa.String(50),
        type_=sa.String(6),
        existing_nullable=True,
    )
    op.create_check_constraint(
        "vehicle_type",
        "vehicles",
        "vehicle_type IN ('SMALL', 'MEDIUM', 'LARGE')",
    )

    op.add_column(
        "customers", sa.Column("deleted_at", sa.DateTime(timezone=True))
    )
    op.create_index("ix_customers_deleted_at", "customers", ["deleted_at"])

    op.add_column(
        "weighing_tasks", sa.Column("deleted_at", sa.DateTime(timezone=True))
    )
    op.add_column("weighing_tasks", sa.Column("deleted_by", sa.Uuid()))
    op.add_column("weighing_tasks", sa.Column("delete_reason", sa.Text()))
    op.create_index(
        "ix_weighing_tasks_deleted_at", "weighing_tasks", ["deleted_at"]
    )

    op.create_table(
        "billing_rules",
        sa.Column("vehicle_type", sa.String(6), nullable=False),
        sa.Column("fee_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("effective_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("fee_amount >= 0", name="ck_billing_rules_fee_nonnegative"),
        sa.CheckConstraint(
            "vehicle_type IN ('SMALL', 'MEDIUM', 'LARGE')",
            name="billing_rule_vehicle_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "vehicle_type",
            "effective_time",
            name="uq_billing_rules_type_effective",
        ),
    )
    op.create_index("ix_billing_rules_vehicle_type", "billing_rules", ["vehicle_type"])
    op.create_index(
        "ix_billing_rules_effective_time", "billing_rules", ["effective_time"]
    )

    op.create_table(
        "billing_records",
        sa.Column("weighing_task_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_type_snapshot", sa.String(6), nullable=False),
        sa.Column("fee_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_status", sa.String(6), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "fee_amount >= 0", name="ck_billing_records_fee_nonnegative"
        ),
        sa.CheckConstraint(
            "vehicle_type_snapshot IN ('SMALL', 'MEDIUM', 'LARGE')",
            name="billing_record_vehicle_type",
        ),
        sa.CheckConstraint(
            "payment_status IN ('UNPAID', 'PAID', 'WAIVED')",
            name="payment_status",
        ),
        sa.ForeignKeyConstraint(
            ["weighing_task_id"], ["weighing_tasks.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"], ["vehicles.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_records_weighing_task_id",
        "billing_records",
        ["weighing_task_id"],
        unique=True,
    )
    op.create_index(
        "ix_billing_records_vehicle_id", "billing_records", ["vehicle_id"]
    )
    op.create_index(
        "ix_billing_records_payment_status",
        "billing_records",
        ["payment_status"],
    )

    billing_rule_table = sa.table(
        "billing_rules",
        sa.column("id", sa.Uuid()),
        sa.column("vehicle_type", sa.String()),
        sa.column("fee_amount", sa.Numeric()),
        sa.column("currency", sa.String()),
        sa.column("effective_time", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    effective_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
    created_at = datetime.now(timezone.utc)
    op.bulk_insert(
        billing_rule_table,
        [
            {
                "id": UUID("10000000-0000-0000-0000-000000000001"),
                "vehicle_type": "SMALL",
                "fee_amount": Decimal("10.00"),
                "currency": "CNY",
                "effective_time": effective_time,
                "created_at": created_at,
            },
            {
                "id": UUID("10000000-0000-0000-0000-000000000002"),
                "vehicle_type": "MEDIUM",
                "fee_amount": Decimal("30.00"),
                "currency": "CNY",
                "effective_time": effective_time,
                "created_at": created_at,
            },
            {
                "id": UUID("10000000-0000-0000-0000-000000000003"),
                "vehicle_type": "LARGE",
                "fee_amount": Decimal("100.00"),
                "currency": "CNY",
                "effective_time": effective_time,
                "created_at": created_at,
            },
        ],
    )


def downgrade() -> None:
    """Remove billing and restore the original free-text vehicle type column."""
    op.drop_index("ix_billing_records_payment_status", table_name="billing_records")
    op.drop_index("ix_billing_records_vehicle_id", table_name="billing_records")
    op.drop_index(
        "ix_billing_records_weighing_task_id", table_name="billing_records"
    )
    op.drop_table("billing_records")
    op.drop_index("ix_billing_rules_effective_time", table_name="billing_rules")
    op.drop_index("ix_billing_rules_vehicle_type", table_name="billing_rules")
    op.drop_table("billing_rules")

    op.drop_index("ix_weighing_tasks_deleted_at", table_name="weighing_tasks")
    op.drop_column("weighing_tasks", "delete_reason")
    op.drop_column("weighing_tasks", "deleted_by")
    op.drop_column("weighing_tasks", "deleted_at")
    op.drop_index("ix_customers_deleted_at", table_name="customers")
    op.drop_column("customers", "deleted_at")

    op.drop_constraint("vehicle_type", "vehicles", type_="check")
    op.alter_column(
        "vehicles",
        "vehicle_type",
        existing_type=sa.String(6),
        type_=sa.String(50),
        existing_nullable=True,
    )
    op.execute(
        "UPDATE vehicles SET vehicle_type = COALESCE(vehicle_type_legacy, vehicle_type)"
    )
    op.drop_index("ix_vehicles_deleted_at", table_name="vehicles")
    op.drop_column("vehicles", "deleted_at")
    op.drop_column("vehicles", "vehicle_type_legacy")
