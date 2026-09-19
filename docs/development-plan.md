# TimberOps 开发路线

本文记录已经落地的能力、当前文档基线工作和候选后续方向。它不是对尚未实现功能的承诺；代码、测试和 Alembic migration 是实现状态的最终依据。

## Completed

| 阶段 | 已完成内容 |
| --- | --- |
| Phase 0 / 0.1 | 系统架构、数据库和业务流程设计；磅房独立领域、通用货物分类、吨制重量、称重状态机与超重复磅设计 |
| Phase 1.1 | FastAPI、SQLAlchemy、Pydantic、Alembic、PostgreSQL 与 pytest 基础工程 |
| Phase 1.2 / 1.3 | 车辆、客户、称重任务与称重记录模型；状态机、REST API、迁移和测试 |
| Phase 2.1 | Vue 3 磅房工作台、车辆/客户/称重页面 |
| Phase 2.2 | 只读 LangGraph Agent、豆包 Provider、AnalyticsService 与五个查询工具 |
| Phase 2.3 | Streamable HTTP MCP Server，复用 AnalyticsService 暴露只读工具 |
| Phase 2.4 | AI Assistant UI 与会话体验 |
| Phase 2.5 | AI Reliability：超时、错误映射和可用性边界 |
| Phase 2.5.1 / 2.5.1.1 | 货物目录、称重流程优化、Excel 历史导出；AI Session 隔离和数据库连接稳定性修复 |
| Phase 2.5.2 | 数据软删除、车辆类型标准化、BillingRule / BillingRecord 与自动计费 |
| Phase 2.5.3.x | User、bcrypt、JWT、RBAC、Bootstrap Admin、操作人审计；前端登录、用户管理和权限菜单 |
| Phase 2.6.1 | Dashboard 真实数据化 |
| Phase 2.6.2 | Billing 管理中心、支付/免除与审计 |
| Phase 2.6.3 / 2.6.3.1 | Audit 日志中心、业务对象可读化与前端注册体验 |
| Phase 2.6.4 | 日/月经营报表与 Excel 导出 |
| Phase 2.7.1 | Backend、Vue/Nginx、PostgreSQL、MCP 的生产 Docker Compose |
| Phase 2.7.2 | 配置、Secret、CORS、JWT、错误响应、API Docs 与容器安全基线 |
| Phase 2.7.3.1 | JSON 请求日志、request id、慢请求检测 |
| Phase 2.7.3.2 | Prometheus-compatible HTTP、AI、称重、计费和连接池指标 |
| Phase 2.7.3.3 | `/health`、数据库 `/ready` 与运行时诊断；readiness 快速失败策略 |

## Current — Phase 2.7.4

- 让根目录、后端、前端及 `docs/` 文档与真实实现一致
- 整理 OpenAPI 标题、版本、业务 tags 和关键端点说明
- 明确当前能力边界、生产启动流程与 v1.0 release blockers
- 形成适合代码审查和作品集展示的统一文档基线

## Planned

以下事项尚未实现，后续按风险和价值单独立项：

- 前端 bundle optimization
- CI / engineering checks
- PostgreSQL backup / restore 流程与恢复演练
- HTTPS / TLS 与完整 deployment checklist
- 真实 weighbridge adapter 及设备故障降级
- 已完成业务的 correction / void workflow
- Portfolio documentation 的持续整理

订单、库存、物料主数据、支付网关、SSO、多租户、RAG 和多 Agent 不属于当前已承诺范围。
