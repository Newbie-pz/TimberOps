"""create RBAC tables and seed grants

Revision ID: e6a1b3c4d520
Revises: d4f8a1c2b390
Create Date: 2026-09-16 20:00:00
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from alembic import op
import sqlalchemy as sa


revision: str = "e6a1b3c4d520"
down_revision: str | Sequence[str] | None = "d4f8a1c2b390"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ROLES: tuple[tuple[str, str], ...] = (
    ("ADMIN", "管理员"),
    ("OPERATOR", "操作员"),
    ("VIEWER", "查看员"),
)

PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("vehicle:create", "创建车辆"),
    ("vehicle:update", "修改车辆"),
    ("vehicle:delete", "删除车辆"),
    ("vehicle:view", "查看车辆"),
    ("customer:create", "创建客户"),
    ("customer:update", "修改客户"),
    ("customer:delete", "删除客户"),
    ("customer:view", "查看客户"),
    ("weighing:create", "创建称重任务"),
    ("weighing:tare", "提交皮重"),
    ("weighing:gross", "提交毛重"),
    ("weighing:complete", "完成称重任务"),
    ("weighing:delete", "删除称重任务"),
    ("weighing:view", "查看称重"),
    ("billing:view", "查看费用"),
    ("billing:update", "修改费用"),
    ("export:data", "导出数据"),
    ("ai:query", "使用 AI 查询"),
    ("user:manage", "管理用户角色"),
)

OPERATOR_PERMISSIONS = frozenset(
    {
        "vehicle:view",
        "vehicle:create",
        "vehicle:update",
        "customer:view",
        "customer:create",
        "weighing:view",
        "weighing:create",
        "weighing:tare",
        "weighing:gross",
        "weighing:complete",
        "billing:view",
        "export:data",
        "ai:query",
    }
)

VIEWER_PERMISSIONS = frozenset(
    {
        "vehicle:view",
        "customer:view",
        "weighing:view",
        "billing:view",
        "export:data",
        "ai:query",
    }
)


def _stable_id(kind: str, value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"timberops:rbac:{kind}:{value}")


def upgrade() -> None:
    """Create normalized RBAC tables and the initial permission matrix."""
    op.create_table(
        "roles",
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_permissions_code",
        "permissions",
        ["code"],
        unique=True,
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "role_id",
            name="uq_user_roles_user_role",
        ),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_role_permissions_role_permission",
        ),
    )
    op.create_index(
        "ix_role_permissions_permission_id",
        "role_permissions",
        ["permission_id"],
    )
    op.create_index(
        "ix_role_permissions_role_id",
        "role_permissions",
        ["role_id"],
    )

    now = datetime.now(timezone.utc)
    role_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
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

    role_ids = {name: _stable_id("role", name) for name, _ in ROLES}
    permission_ids = {
        code: _stable_id("permission", code) for code, _ in PERMISSIONS
    }
    op.bulk_insert(
        role_table,
        [
            {
                "id": role_ids[name],
                "name": name,
                "description": description,
                "created_at": now,
                "updated_at": now,
            }
            for name, description in ROLES
        ],
    )
    op.bulk_insert(
        permission_table,
        [
            {
                "id": permission_ids[code],
                "code": code,
                "name": name,
                "description": name,
                "created_at": now,
            }
            for code, name in PERMISSIONS
        ],
    )

    all_permission_codes = frozenset(permission_ids)
    grants = {
        "ADMIN": all_permission_codes,
        "OPERATOR": OPERATOR_PERMISSIONS,
        "VIEWER": VIEWER_PERMISSIONS,
    }
    op.bulk_insert(
        role_permission_table,
        [
            {
                "id": _stable_id("grant", f"{role_name}:{permission_code}"),
                "role_id": role_ids[role_name],
                "permission_id": permission_ids[permission_code],
            }
            for role_name, permission_codes in grants.items()
            for permission_code in sorted(permission_codes)
        ],
    )


def downgrade() -> None:
    """Drop all RBAC associations and catalog tables."""
    op.drop_index(
        "ix_role_permissions_role_id",
        table_name="role_permissions",
    )
    op.drop_index(
        "ix_role_permissions_permission_id",
        table_name="role_permissions",
    )
    op.drop_table("role_permissions")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
