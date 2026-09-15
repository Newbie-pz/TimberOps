# TimberOps Backend

TimberOps 后端负责 HTTP API、应用配置、数据库访问、称重领域能力和只读业务智能查询。当前完成 Phase 2.3：除 LangGraph Agent 外，外部 Agent 还可通过标准 MCP Streamable HTTP 协议调用同一组查询能力。

## 技术栈

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- Pydantic v2 与 pydantic-settings
- Alembic
- PostgreSQL（psycopg 3）
- pytest
- LangGraph、LangChain Core、LangChain OpenAI
- MCP Python SDK

Phase 2.2 已验证版本：LangGraph 1.2.11、LangChain Core 1.6.3、LangChain OpenAI 1.6.2。
Phase 2.3 已验证 MCP Python SDK 2.2.0。

## 目录结构

```text
backend/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── api/
│   │   ├── exceptions.py    # 统一领域异常转换
│   │   ├── router.py        # 顶层 APIRouter 与健康检查
│   │   └── v1/              # Vehicle、Customer、Weighing REST API
│   ├── core/
│   │   └── config.py        # 环境变量配置
│   ├── db/
│   │   ├── base.py          # SQLAlchemy DeclarativeBase
│   │   └── session.py       # Engine、SessionLocal、get_db
│   ├── domain/              # 枚举、异常和纯 Decimal 称重计算
│   ├── models/              # 五个核心 SQLAlchemy 模型
│   ├── schemas/             # Pydantic v2 输入/读取模型
│   ├── services/            # 状态机服务与只读 AnalyticsService
│   └── integrations/
│       ├── ai/
│       │   ├── providers/   # 可替换的 LLM Provider 与豆包实现
│       │   ├── tools/       # 只读称重业务工具
│       │   └── agent/       # LangGraph 状态、Prompt 与 Graph
│       └── mcp/
│           ├── server.py    # 独立 Streamable HTTP ASGI Server
│           ├── tools.py     # AnalyticsService 的 MCP 适配器
│           └── schemas.py   # MCP 强类型结构化输出
├── migrations/
│   ├── env.py               # Alembic 环境
│   └── versions/            # 数据库版本脚本
├── tests/
│   └── test_health.py
├── alembic.ini
├── requirements.txt
└── Dockerfile
```

## 配置

配置通过系统环境变量或 `.env` 加载。后端从当前目录的 `.env` 或项目根目录的 `.env` 读取：

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/timberops
APP_NAME=TimberOps backend
DEBUG=false
AI_ENABLED=false
LLM_PROVIDER=doubao
DOUBAO_API_KEY=
DOUBAO_BASE_URL=
DOUBAO_MODEL=
AI_TEMPERATURE=0
MCP_HOST=127.0.0.1
MCP_PORT=8001
```

不要提交真实密码。项目根目录已提供 `.env.example`。

健康检查不访问数据库；使用数据库或 Alembic 时必须提供 `DATABASE_URL`。

## 本地启动

在项目根目录创建 `.env` 后：

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

访问：

- 健康检查：`http://localhost:8000/health`
- Swagger UI：`http://localhost:8000/docs`
- OpenAPI JSON：`http://localhost:8000/openapi.json`

## REST API

所有业务接口使用 `/api/v1` 前缀：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST / GET | `/api/v1/vehicles` | 创建、列出车辆 |
| GET / PATCH | `/api/v1/vehicles/{id}` | 查询、更新车辆档案 |
| POST / GET | `/api/v1/customers` | 创建、列出客户 |
| GET / PATCH | `/api/v1/customers/{id}` | 查询、更新客户 |
| POST / GET | `/api/v1/weighing/tasks` | 创建、过滤查询称重任务 |
| GET | `/api/v1/weighing/tasks/{id}` | 任务汇总及完整历史 |
| GET | `/api/v1/weighing/tasks/{id}/records` | 按序查询称重读数 |
| POST | `/api/v1/weighing/tasks/{id}/tare` | 记录皮重 |
| POST | `/api/v1/weighing/tasks/{id}/loading` | 开始装货 |
| POST | `/api/v1/weighing/tasks/{id}/wait-gross` | 装货完成，等待毛重 |
| POST | `/api/v1/weighing/tasks/{id}/gross` | 记录首次毛重并判定 |
| POST | `/api/v1/weighing/tasks/{id}/reweigh` | 超重卸货后复磅 |
| POST | `/api/v1/weighing/tasks/{id}/complete` | 完成正常任务 |
| POST | `/api/v1/ai/chat` | 只读业务 Agent 问答 |

任务列表支持 `cargo_type`、`status`、`vehicle_id` 查询参数。

## 只读 AI Agent

```text
User
  ↓
TimberOps Agent（LangGraph）
  ↓
LLM Provider / Doubao
  ↕ Tool Calling
Read-only Business Tools
  ↓
AnalyticsService
  ↓
SQLAlchemy / PostgreSQL
```

Agent 不持有 SQL 工具，也不直接访问 Session。模型只能选择以下固定工具，工具只调用 `AnalyticsService`：

- `get_today_weighing_summary`
- `get_cargo_weight_summary`
- `get_overweight_records`
- `get_vehicle_weighing_history`
- `get_weighing_task_detail`

Agent 当前只能查询、统计、分析和解释，不能创建或修改车辆、客户、称重任务与称重记录。响应中的 `tool_calls` 只公开工具名称、参数和执行状态，不公开隐藏推理过程。

示例请求：

```http
POST /api/v1/ai/chat
Content-Type: application/json

{"message": "今天煤炭称了多少吨？"}
```

可提问示例：

- “今天煤炭称了多少吨？”
- “今天有没有超重车辆？”
- “蒙H12345 最近称过什么货？”
- “查询 WT-xxxx 的称重历史。”

AI 默认关闭。只有调用 Agent API 时才检查 Provider 配置；缺少配置或 `AI_ENABLED=false` 时返回 `503 AI_SERVICE_UNAVAILABLE`，健康检查和原有业务 API 继续正常工作。

豆包配置步骤：

1. 在火山方舟创建 API Key 和可调用的模型/推理接入点。
2. 复制根目录 `.env.example` 为 `.env`。
3. 设置 `AI_ENABLED=true`、`DOUBAO_API_KEY`、`DOUBAO_BASE_URL` 和 `DOUBAO_MODEL`。
4. 重启后端。模型 ID 和 Base URL 均由环境提供，源码不内置具体值。

LangGraph 使用单 Agent 循环：`START → Agent → (ToolNode → Agent)* → END`。首版不保存会话记忆。

## MCP Server

Phase 2.3 增加独立、无状态的 Streamable HTTP MCP Server：

```text
External Agent / MCP Client
  ↓ Streamable HTTP
TimberOps MCP Tools
  ↓
AnalyticsService
  ↓
SQLAlchemy / PostgreSQL
```

启动：

```powershell
python -m app.integrations.mcp.server
```

默认连接地址：`http://127.0.0.1:8001/mcp`。也可以将 ASGI 应用交给 Uvicorn：

```powershell
python -m uvicorn app.integrations.mcp.server:app --host 127.0.0.1 --port 8001
```

服务使用无状态 Streamable HTTP 和 JSON response，提供与 Agent 相同的五项查询能力。每个工具同时发布输入、输出 JSON Schema 和结构化结果，并带有 `readOnlyHint=true`、`openWorldHint=false` 标记。

当前默认只监听本机地址，尚未实现公网身份认证；部署到非本机域名前必须先设计认证、授权、TLS 和允许的 Host/Origin。

### MCP 与 LangGraph Agent 的区别

| 能力 | LangGraph Agent | MCP Server |
| --- | --- | --- |
| 使用者 | TimberOps `/api/v1/ai/chat` | 外部 MCP Host / Agent |
| 自然语言回答 | 由豆包生成 | 不生成，只返回结构化数据 |
| 工具选择 | TimberOps 内部 LLM 自主选择 | 外部 MCP 客户端选择 |
| 查询实现 | AnalyticsService | 同一个 AnalyticsService |
| 数据写入 | 禁止 | 禁止 |

MCP 层不依赖 LangGraph，也没有复制 SQL；两条入口只共享确定性的只读查询服务。

领域错误统一返回：

```json
{
  "error": {
    "code": "INVALID_STATE",
    "message": "human readable message"
  }
}
```

资源不存在为 `404 RESOURCE_NOT_FOUND`；非法状态为 `409 INVALID_STATE`；重复车牌、超重完成等为 `409 BUSINESS_CONFLICT`；请求参数验证保持 FastAPI 默认 422。

运行测试：

```powershell
python -m pytest
```

运行 Alembic：

```powershell
python -m alembic current
python -m alembic upgrade head
```

当前迁移 `2e11a7a8e890_create_weighing_core_tables.py` 创建：

- `vehicles`
- `customers`
- `weighing_tasks`
- `weighing_records`
- `audit_logs`

`app/models/__init__.py` 会注册全部模型，Alembic 的 `target_metadata` 指向统一 `Base.metadata`。

## 称重领域约定

- UUID 作为五个核心实体的一致主键。
- 重量使用 Python `Decimal` 和 PostgreSQL `NUMERIC(10,3)`，业务单位为吨。
- `WeighingTask` 保存当前有效汇总；`WeighingRecord` 追加保存每次真实读数。
- 任务创建时复制车辆核定总质量和司机信息，车辆档案修改不影响历史快照。
- `status` 与 `weight_result` 分离，所有状态迁移只能由 `WeighingService` 执行。
- 超重后任务返回 `WAIT_GROSS`，后续必须追加带原因的 `REWEIGH`。
- `COMPLETED` 和 `CANCELLED` 都不能恢复称重流程。
- 取消原因与状态变化写入 `AuditLog`。

本阶段没有创建 `order_id`。Order 表尚不存在，此时保留无外键逻辑字段会允许悬空引用；后续实现 Order 时再通过 Alembic 增加 nullable 外键。

## Docker 启动

先构建后端镜像：

```powershell
docker build -t timberops-backend .\backend
```

运行时通过环境文件提供配置；容器内连接根 Compose 的数据库时，应使用可解析的数据库主机名，而不是 `localhost`：

```powershell
docker run --rm -p 8000:8000 --env-file .env timberops-backend
```

Phase 1.2 仍未把后端服务加入根目录 `docker-compose.yml`。在后续 Compose 集成前，上述容器命令要求 `.env` 中的数据库地址可从容器访问；健康检查本身不连接数据库。

## 当前实现范围

已完成：

- FastAPI 应用工厂和统一 APIRouter
- `GET /health`
- pydantic-settings 配置
- SQLAlchemy Engine、SessionLocal 和请求依赖
- Vehicle、Customer、WeighingTask、WeighingRecord、AuditLog
- Pydantic v2 创建、更新、读取与称重命令 Schema
- Decimal 称重计算、合法状态迁移、超重复磅和取消审计
- Alembic 首个业务迁移
- Vehicle、Customer 和 Weighing REST API
- 统一业务异常响应
- Swagger/OpenAPI 完整称重闭环
- Dockerfile
- 健康检查及称重领域测试
- 只读 AnalyticsService 和五个结构化业务 Tool
- 可替换 LLM Provider 与豆包 Provider
- LangGraph Tool Calling Agent 和 `/api/v1/ai/chat`
- 不调用真实模型的 Stub Agent 测试
- MCP Streamable HTTP Server、五个结构化查询工具和协议级测试

未实现：用户、认证、RBAC、Order、Inventory、Material、磅单打印、真实设备、Agent 前端、MCP 远程认证、RAG 和多 Agent。
