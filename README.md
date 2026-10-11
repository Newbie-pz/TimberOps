# TimberOps

[![CI](https://github.com/Newbie-pz/TimberOps/actions/workflows/ci.yml/badge.svg)](https://github.com/Newbie-pz/TimberOps/actions/workflows/ci.yml)

TimberOps 是面向中小型货运与加工场景的车辆称重和经营管理系统。当前支持木材、煤炭、矿石及其他货物，提供从车辆与客户建档、称重、超重复磅到计费、审计、报表和历史冲正的完整闭环。

当前代码版本为 **v1.0.0**。这是可运行、可部署且经过自动化测试的代码 Release；它不代表已经完成特定公网环境的域名、可信证书、防火墙或真实地磅厂商联调。

## 已实现能力

- 车辆、客户管理及历史数据保护
- 人工皮重、毛重、超重复磅、任务完成和称重历史
- Manual / Simulator Weighbridge Adapter，以及未来真实设备协议的稳定接入边界
- 已完成业务的不可变冲正：保留原任务、读数、费用和完整审计链
- Excel 称重历史及日/月经营报表导出
- 完成称重后按车辆类型自动生成费用，支持支付与免除
- 真实数据 Dashboard、费用中心、审计日志和经营报表
- JWT 登录、公开注册开关、待授权账号体验、ADMIN / OPERATOR / VIEWER RBAC
- Bootstrap Admin 安全初始化与最后一个管理员保护
- 只读 LangGraph AI Agent 和豆包 Provider（可选）
- 面向外部 Agent 的 Streamable HTTP MCP Server（只读）
- 开发与生产 Docker Compose、Nginx 前端入口、PostgreSQL 持久化
- 可选 Nginx TLS overlay、HTTP→HTTPS 重定向及生产 Edge 安全边界
- 结构化请求日志、Prometheus-compatible Metrics、`/health` 与 `/ready`
- GitHub Actions CI、Ruff、pytest coverage、前后端构建与 migration 检查
- PostgreSQL 自定义格式备份、SHA-256 manifest 与非覆盖恢复验证工具

## 系统架构

```mermaid
flowchart TB
    Browser[Browser] --> Web[Nginx / Vue SPA]
    Web --> API[FastAPI]
    API --> PG[(PostgreSQL)]
    API --> W[Weighing]
    API --> B[Billing]
    API --> D[Dashboard / Reports]
    API --> AU[Audit]
    API --> AR[Auth / RBAC]
    API --> Agent[LangGraph read-only Agent]
    Agent --> Analytics[AnalyticsService]
    Analytics --> PG
    MCPClient[External MCP Client] --> MCP[MCP Server]
    MCP --> Analytics
```

内部 LangGraph Agent 与外部 MCP Server 是两条独立入口；两者复用只读 `AnalyticsService`，AI 不可用不会阻塞核心称重业务。

## 核心业务流程

正式任务状态为：

`WAIT_TARE → TARE_COMPLETED → WAIT_GROSS → GROSS_COMPLETED → COMPLETED`

`status` 表示任务生命周期；`weight_result` 独立表示 `PENDING / NORMAL / OVERWEIGHT`。超重时任务回到 `WAIT_GROSS`，接受重新称重，直至结果正常后完成。重量统一使用吨和 `Decimal`。

已完成任务保持不可变。发现历史录入错误时，由 ADMIN 创建独立冲正记录，原任务、称重读数与费用仍完整保留；经营统计排除已冲正业务，操作员随后另行创建正确任务。已支付费用因当前没有退款模型而禁止直接冲正。

## 技术栈

- 后端：Python 3.11+、FastAPI、SQLAlchemy 2、Pydantic 2、Alembic、PostgreSQL、pytest
- 前端：Vue 3、TypeScript、Vite、Element Plus、Pinia、Axios
- AI / 集成：LangGraph、豆包 Provider、MCP Python SDK
- 运行：Docker Compose、Nginx、Prometheus client

## 本地开发

```powershell
Copy-Item .env.example .env
# 修改 .env 中的数据库密码、DATABASE_URL 和 JWT_SECRET_KEY
docker compose up -d db

cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alembic upgrade head
python -m app.cli.bootstrap_admin
python -m uvicorn app.main:app --reload
```

另开终端启动前端：

```powershell
cd frontend
npm install
npm run dev
```

默认开发入口为 `http://localhost:5173`。API 文档仅在 `ENABLE_API_DOCS=true` 时开放。

## Production Compose 快速启动

```powershell
Copy-Item .env.example .env
# 至少修改 POSTGRES_PASSWORD、DATABASE_URL_DOCKER、JWT_SECRET_KEY、FRONTEND_PORT
# AI 配置可选；生产建议 PUBLIC_REGISTRATION_ENABLED=false
docker compose -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

不要提交 `.env`。生产数据库地址必须使用 Compose 服务名 `db`，且 `DATABASE_URL_DOCKER` 中的密码要与 `POSTGRES_PASSWORD` 一致。

## 运维端点

| 端点 | 用途 |
| --- | --- |
| `GET /health` | 进程存活检查，不访问数据库 |
| `GET /ready` | PostgreSQL 就绪检查，采用短生命周期快速失败连接 |
| `GET /metrics` | Prometheus 文本格式；由 `ENABLE_METRICS` 控制 |
| `GET /docs` | Swagger UI；由 `ENABLE_API_DOCS` 控制 |

## 演示与作品集

仓库不包含伪造的产品截图。建议按 [作品集截图清单](docs/portfolio.md) 使用真实运行环境采集 Dashboard、称重工作台、冲正、费用、报表、审计、AI、RBAC 和 CI 页面。v1.0 功能摘要见 [Release Notes](docs/release-notes-v1.0.md)。

## 文档

- [系统架构](docs/architecture.md)
- [业务流程](docs/business-flow.md)
- [数据库设计](docs/database-design.md)
- [开发路线](docs/development-plan.md)
- [生产部署](docs/deployment.md)
- [安全基线](docs/security.md)
- [可观测性](docs/observability.md)
- [Metrics](docs/metrics.md)
- [工程质量与 CI](docs/engineering.md)
- [v1.0 发布检查清单](docs/release-checklist.md)
- [v1.0 Release Notes](docs/release-notes-v1.0.md)
- [作品集截图清单](docs/portfolio.md)
- [PostgreSQL 恢复演练记录](docs/recovery-drill.md)
- [HTTPS/TLS 隔离演练记录](docs/tls-drill.md)
- [后端说明](backend/README.md)
- [前端说明](frontend/README.md)

## 当前边界

当前已实现 Manual 与 Simulator 地磅适配器、HTTPS 部署能力、备份/恢复、CI 和不可变冲正。尚未完成具体厂商真实地磅协议联调、公网可信 CA 上线、远程 MCP 应用层认证或完整退款/资金流水；也没有订单、库存、支付网关、SSO、多租户、RAG 或多 Agent 编排。MCP 默认仅绑定回环地址。

## Production / v1.0 Checklist

- [ ] 使用强 PostgreSQL 密码并完成发布前 Secret 扫描
- [ ] 为每个环境生成独立且足够长的 JWT Secret
- [ ] 明确并验证公开注册策略
- [x] 提供并隔离验证 Nginx HTTPS/TLS 部署能力
- [ ] 为实际公网域名安装可信 CA 证书并确认续期责任
- [x] 建立手动数据库备份/非覆盖恢复工具并完成 PostgreSQL 16 隔离演练
- [ ] 远程暴露 MCP 时增加认证和访问控制
- [ ] 接入真实磅秤前完成设备协议与故障降级验证
