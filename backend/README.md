# TimberOps Backend

TimberOps 后端是一个 FastAPI 模块化单体，负责认证授权、车辆与客户、称重状态机、计费、审计、Dashboard、报表、只读 AI 与 MCP 查询。PostgreSQL 是唯一业务数据源，数据库结构由 Alembic 管理。

## 技术栈与目录

Python 3.11+、FastAPI、SQLAlchemy 2、Pydantic 2、pydantic-settings、Alembic、psycopg 3、PostgreSQL、pytest、LangGraph、MCP Python SDK、prometheus-client。

```text
backend/
├── app/
│   ├── api/                 # HTTP routers、依赖与异常映射
│   ├── cli/                 # Bootstrap Admin 等运维命令
│   ├── core/                # 环境配置
│   ├── db/                  # Engine、Session、Base
│   ├── domain/              # 枚举、状态机、RBAC Catalog
│   ├── integrations/        # AI 与 MCP
│   ├── middleware/          # 结构化请求日志
│   ├── models/              # SQLAlchemy ORM
│   ├── observability/       # Prometheus Metrics
│   ├── schemas/             # API DTO
│   ├── security/            # bcrypt、JWT、RBAC dependencies
│   ├── services/            # 事务与业务服务
│   └── main.py
├── migrations/              # Alembic revisions
├── scripts/                 # 安全检查
└── tests/
```

## 配置与启动

配置由根目录 `.env` 注入；不要在代码或仓库中保存密码、JWT Secret 或 AI Key。

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

首个管理员必须显式执行 `python -m app.cli.bootstrap_admin` 初始化。

## 实际 API

业务 API 使用 `/api/v1` 前缀；下表只列出当前 router 中存在的路径。

| 模块 | 方法与路径 |
| --- | --- |
| Auth | `GET /auth/registration-status`、`POST /auth/register`、`POST /auth/login`、`GET /auth/me`、`GET /auth/roles`、`GET /auth/permissions` |
| Users / RBAC | `GET /users`、`POST /users`、`GET /users/roles`、`POST /users/{user_id}/roles`、`DELETE /users/{user_id}/roles/{role_id}` |
| Vehicles | `GET/POST /vehicles`、`GET/PATCH/DELETE /vehicles/{vehicle_id}` |
| Customers | `GET/POST /customers`、`GET/PATCH/DELETE /customers/{customer_id}` |
| Weighing | `GET /weighing/cargo-catalog`、`GET/POST /weighing/tasks`、`GET/DELETE /weighing/tasks/{task_id}`、`GET /weighing/tasks/{task_id}/records` |
| Weighing actions | `POST /weighing/tasks/{task_id}/tare`、`/loading`、`/wait-gross`、`/gross`、`/reweigh`、`/complete` |
| Billing | `GET /billing/records`、`PATCH /billing/records/{record_id}/pay`、`PATCH /billing/records/{record_id}/waive` |
| Dashboard | `GET /dashboard/overview` |
| Audit | `GET /audit/logs` |
| Reports | `GET /reports/daily`、`GET /reports/monthly`、`GET /reports/export` |
| Export | `GET /export/weighing` |
| AI | `POST /ai/chat` |

根级运维端点为 `GET /health`、`GET /ready` 和 `GET /metrics`。`/loading` 是旧客户端兼容入口，不代表正式状态机中存在 `LOADING` 状态。

## 安全与业务边界

- 密码仅保存 bcrypt hash；登录签发 HS256 JWT，包含 `sub`、`username`、`iat`、`jti`、`exp`。
- 角色为 `ADMIN`、`OPERATOR`、`VIEWER`；权限定义以 `app/domain/rbac_catalog.py` 为准。
- 公开注册关闭时注册接口拒绝请求；注册成功账号没有默认角色。
- 前端隐藏仅改善体验，后端 `require_permission()` 是授权边界；审计操作人来自 JWT。
- 正式状态流是 `WAIT_TARE → TARE_COMPLETED → WAIT_GROSS → GROSS_COMPLETED → COMPLETED`；超重由独立 `weight_result` 表示。
- 仅任务成功完成时，按生效车辆类型规则生成唯一 `BillingRecord`。

## AI Agent 与 MCP

LangGraph Agent 服务于应用内 AI Chat；MCP Server 服务于外部 MCP Client。它们是独立入口，均复用只读 `AnalyticsService`，不直接写 SQL。AI 由 `AI_ENABLED` 控制，核心称重不依赖 AI。

```powershell
python -m app.integrations.mcp.server
```

## 数据库与测试

```powershell
python -m alembic upgrade head
python -m alembic check
python -m pytest
python ..\scripts\security_check.py
```

禁止修改历史 migration。当前模型见 [数据库设计](../docs/database-design.md)，部署、安全和观测见 [deployment](../docs/deployment.md)、[security](../docs/security.md)、[observability](../docs/observability.md)。

当前未实现订单、库存、物料主数据、支付网关、Refresh Token、JWT 撤销列表、真实磅秤适配器、冲正/作废流程；MCP 远程暴露尚无应用层认证。
