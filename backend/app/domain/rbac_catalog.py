"""Canonical roles and permissions seeded by the RBAC migration."""

ROLE_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("ADMIN", "管理员"),
    ("OPERATOR", "操作员"),
    ("VIEWER", "查看员"),
)

PERMISSION_DEFINITIONS: tuple[tuple[str, str], ...] = (
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
    ("billing:waive", "免除费用"),
    ("export:data", "导出数据"),
    ("ai:query", "使用 AI 查询"),
    ("user:manage", "管理用户角色"),
    ("dashboard:view", "查看运营看板"),
    ("audit:view", "查看审计日志"),
    ("report:view", "查看业务报表"),
    ("report:export", "导出业务报表"),
)

OPERATOR_PERMISSION_CODES: frozenset[str] = frozenset(
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
        "billing:update",
        "export:data",
        "ai:query",
        "dashboard:view",
        "audit:view",
        "report:view",
        "report:export",
    }
)

VIEWER_PERMISSION_CODES: frozenset[str] = frozenset(
    {
        "vehicle:view",
        "customer:view",
        "weighing:view",
        "billing:view",
        "export:data",
        "ai:query",
        "dashboard:view",
        "report:view",
    }
)

ROLE_PERMISSION_CODES: dict[str, frozenset[str]] = {
    "ADMIN": frozenset(code for code, _ in PERMISSION_DEFINITIONS),
    "OPERATOR": OPERATOR_PERMISSION_CODES,
    "VIEWER": VIEWER_PERMISSION_CODES,
}
