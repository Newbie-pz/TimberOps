"""create weighing core tables

Revision ID: 2e11a7a8e890
Revises: 
Create Date: 2026-09-15 15:43:03.851451
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision: str = '2e11a7a8e890'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision."""
    op.create_table('audit_logs',
    sa.Column('operator_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('target_type', sa.String(length=64), nullable=False),
    sa.Column('target_id', sa.Uuid(), nullable=True),
    sa.Column('before_value', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True),
    sa.Column('after_value', sa.JSON().with_variant(postgresql.JSONB(), 'postgresql'), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_operator_id'), 'audit_logs', ['operator_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_target_id'), 'audit_logs', ['target_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_target_type'), 'audit_logs', ['target_type'], unique=False)
    op.create_table('customers',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('contact_name', sa.String(length=100), nullable=True),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('remark', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_name'), 'customers', ['name'], unique=False)
    op.create_table('vehicles',
    sa.Column('plate_number', sa.String(length=20), nullable=False),
    sa.Column('driver_name', sa.String(length=100), nullable=True),
    sa.Column('driver_phone', sa.String(length=32), nullable=True),
    sa.Column('vehicle_type', sa.String(length=50), nullable=True),
    sa.Column('allowed_gross_weight_tons', sa.Numeric(precision=10, scale=3), nullable=False),
    sa.Column('remark', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('allowed_gross_weight_tons > 0', name='ck_vehicles_allowed_gross_weight_positive'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vehicles_plate_number'), 'vehicles', ['plate_number'], unique=True)
    op.create_table('weighing_tasks',
    sa.Column('task_no', sa.String(length=40), nullable=False),
    sa.Column('vehicle_id', sa.Uuid(), nullable=False),
    sa.Column('customer_id', sa.Uuid(), nullable=True),
    sa.Column('weighing_direction', sa.Enum('OUTBOUND', 'INBOUND', name='weighing_direction', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('cargo_type', sa.Enum('ORE', 'COAL', 'TIMBER', 'OTHER', name='cargo_type', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('cargo_name', sa.String(length=100), nullable=True),
    sa.Column('cargo_remark', sa.Text(), nullable=True),
    sa.Column('driver_name_snapshot', sa.String(length=100), nullable=True),
    sa.Column('driver_phone_snapshot', sa.String(length=32), nullable=True),
    sa.Column('tare_weight_tons', sa.Numeric(precision=10, scale=3), nullable=True),
    sa.Column('gross_weight_tons', sa.Numeric(precision=10, scale=3), nullable=True),
    sa.Column('net_weight_tons', sa.Numeric(precision=10, scale=3), nullable=True),
    sa.Column('allowed_gross_weight_tons', sa.Numeric(precision=10, scale=3), nullable=False),
    sa.Column('overweight_tons', sa.Numeric(precision=10, scale=3), nullable=False),
    sa.Column('status', sa.Enum('WAIT_TARE', 'TARE_COMPLETED', 'LOADING', 'WAIT_GROSS', 'GROSS_COMPLETED', 'COMPLETED', 'CANCELLED', name='weighing_status', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('weight_result', sa.Enum('PENDING', 'NORMAL', 'OVERWEIGHT', name='weight_result', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('tare_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('gross_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("cargo_type != 'OTHER' OR (cargo_name IS NOT NULL AND length(trim(cargo_name)) > 0)", name='ck_weighing_tasks_other_has_cargo_name'),
    sa.CheckConstraint('allowed_gross_weight_tons > 0', name='ck_weighing_tasks_allowed_gross_weight_positive'),
    sa.CheckConstraint('gross_weight_tons IS NULL OR gross_weight_tons > 0', name='ck_weighing_tasks_gross_positive'),
    sa.CheckConstraint('gross_weight_tons IS NULL OR tare_weight_tons IS NULL OR gross_weight_tons > tare_weight_tons', name='ck_weighing_tasks_gross_above_tare'),
    sa.CheckConstraint('net_weight_tons IS NULL OR net_weight_tons > 0', name='ck_weighing_tasks_net_positive'),
    sa.CheckConstraint('overweight_tons >= 0', name='ck_weighing_tasks_overweight_nonnegative'),
    sa.CheckConstraint('tare_weight_tons IS NULL OR tare_weight_tons > 0', name='ck_weighing_tasks_tare_positive'),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_weighing_tasks_customer_id'), 'weighing_tasks', ['customer_id'], unique=False)
    op.create_index(op.f('ix_weighing_tasks_status'), 'weighing_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_weighing_tasks_task_no'), 'weighing_tasks', ['task_no'], unique=True)
    op.create_index(op.f('ix_weighing_tasks_vehicle_id'), 'weighing_tasks', ['vehicle_id'], unique=False)
    op.create_index(op.f('ix_weighing_tasks_weight_result'), 'weighing_tasks', ['weight_result'], unique=False)
    op.create_table('weighing_records',
    sa.Column('weighing_task_id', sa.Uuid(), nullable=False),
    sa.Column('weight_type', sa.Enum('TARE', 'GROSS', 'REWEIGH', name='weight_type', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('weight_tons', sa.Numeric(precision=10, scale=3), nullable=False),
    sa.Column('sequence_no', sa.Integer(), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('recorded_by', sa.Uuid(), nullable=True),
    sa.Column('source', sa.Enum('MANUAL', 'DEVICE', name='weight_source', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('remark', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('sequence_no > 0', name='ck_weighing_records_sequence_positive'),
    sa.CheckConstraint('weight_tons > 0', name='ck_weighing_records_weight_positive'),
    sa.ForeignKeyConstraint(['weighing_task_id'], ['weighing_tasks.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('weighing_task_id', 'sequence_no', name='uq_weighing_records_task_sequence')
    )
    op.create_index(op.f('ix_weighing_records_weighing_task_id'), 'weighing_records', ['weighing_task_id'], unique=False)


def downgrade() -> None:
    """Revert this revision."""
    op.drop_index(op.f('ix_weighing_records_weighing_task_id'), table_name='weighing_records')
    op.drop_table('weighing_records')
    op.drop_index(op.f('ix_weighing_tasks_weight_result'), table_name='weighing_tasks')
    op.drop_index(op.f('ix_weighing_tasks_vehicle_id'), table_name='weighing_tasks')
    op.drop_index(op.f('ix_weighing_tasks_task_no'), table_name='weighing_tasks')
    op.drop_index(op.f('ix_weighing_tasks_status'), table_name='weighing_tasks')
    op.drop_index(op.f('ix_weighing_tasks_customer_id'), table_name='weighing_tasks')
    op.drop_table('weighing_tasks')
    op.drop_index(op.f('ix_vehicles_plate_number'), table_name='vehicles')
    op.drop_table('vehicles')
    op.drop_index(op.f('ix_customers_name'), table_name='customers')
    op.drop_table('customers')
    op.drop_index(op.f('ix_audit_logs_target_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_target_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_operator_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_table('audit_logs')
