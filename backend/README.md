# Backend

FastAPI 后端目录。Phase 0 仅建立分层骨架，不包含可运行应用。

计划结构：

- `app/api`：版本化路由、请求依赖和 HTTP 边界
- `app/core`：配置、安全、日志和异常处理
- `app/db`：数据库会话与持久化基础设施
- `app/modules`：身份、客户、车辆、物料、订单、称重、库存和审计模块
- `app/integrations/ai`：未来 AI/MCP 适配边界，当前保持空白
- `migrations`：Alembic 迁移
- `tests`：单元测试、集成测试

Phase 1 将补充 `pyproject.toml`、应用入口、Alembic 配置和 Dockerfile。
