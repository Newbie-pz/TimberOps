# TimberOps

TimberOps 是面向中小型木材加工企业的智能运营与车辆称重管理平台。系统包含可独立运行的磅房模块，并逐步覆盖客户、订单、木材库存、出入库和审计。

> 当前状态：Phase 1.1 Backend Foundation。后端基础应用和健康检查已建立，尚未提供业务 API 或前端页面。

## 业务定位

磅房不依赖木材订单，可为运输矿石、煤炭、木材或其他货物的车辆独立完成登记、两次称重、超重判断、复磅和磅单留痕。

- `vehicle_id` 必填。
- `cargo_type` 必填，V1 固定为 `ORE / COAL / TIMBER / OTHER`，前端使用下拉框。
- `customer_id`、`order_id` 均可选。
- 木材运输可选择关联 TimberOps 内部订单；普通过磅无需订单或库存记录。
- 称重净重只是运输称重事实，不自动等同于订单履约量或库存变化。

V1 支持“空车进厂、装货后重车出厂”，默认称重方向为 `OUTBOUND`。架构为未来增加 `INBOUND` 反向称重流程预留扩展点，但当前不实现。

## 核心称重规则

所有核心称重数据统一使用吨（t），数据库使用 `NUMERIC(10, 3)`，应用层使用 `Decimal`，禁止使用浮点数。

```text
net_weight_tons = gross_weight_tons - tare_weight_tons
overweight_tons = max(gross_weight_tons - allowed_gross_weight_tons, 0)
```

任务创建时保存车辆核定总质量 `allowed_gross_weight_tons` 的快照。车辆档案以后发生变化，不影响历史任务和磅单。

流程状态与称重结果彻底分离：

- `status`：`WAIT_TARE / TARE_COMPLETED / LOADING / WAIT_GROSS / GROSS_COMPLETED / COMPLETED / CANCELLED`
- `weight_result`：`PENDING / NORMAL / OVERWEIGHT`

超重车辆不得完成出厂，必须卸货、返回 `WAIT_GROSS` 并追加一条复磅记录。历史读数不可覆盖；只有最新有效的正常读数才能作为任务最终重量。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11+、FastAPI、SQLAlchemy 2.x、Pydantic、Alembic、pytest |
| 前端 | Vue 3、TypeScript、Vite、Element Plus |
| 数据库 | PostgreSQL |
| 基础设施 | Docker Compose、Git |

项目采用模块化单体架构。称重、订单和库存拥有各自业务边界，需要关联时通过显式应用用例协调，而不是由称重完成隐式修改库存。

## 仓库结构

```text
TimberOps/
├── backend/
│   ├── app/
│   │   ├── api/             # HTTP 路由与依赖
│   │   ├── core/            # 配置、安全、异常等横切能力
│   │   ├── db/              # 数据库基础设施
│   │   ├── models/          # SQLAlchemy 模型（Phase 1.2 开始实现）
│   │   ├── schemas/         # Pydantic 请求与响应模型
│   │   ├── services/        # 应用服务与业务用例
│   │   └── integrations/ai/ # 未来 AI/MCP 边界（当前不实现）
│   ├── migrations/          # Alembic 迁移
│   └── tests/               # 自动化测试
├── frontend/                # Vue 前端骨架
├── docs/                    # 架构、数据库、流程与计划
├── .env.example
└── docker-compose.yml
```

## 本地准备

1. 安装 Docker Desktop 或兼容 Docker Compose 的运行时。
2. 复制配置示例：

   ```powershell
   Copy-Item .env.example .env
   ```

3. 修改 `.env` 中的本地密码，不要提交真实凭据。
4. 启动 PostgreSQL：

   ```powershell
   docker compose up -d db
   ```

Phase 1 才会加入可运行的后端、前端和对应容器。

## 文档

- [系统架构](docs/architecture.md)
- [数据库设计](docs/database-design.md)
- [业务流程](docs/business-flow.md)
- [开发计划](docs/development-plan.md)

## 工程约定

- 数据库结构变更必须通过 Alembic 管理。
- 配置来自环境变量，禁止硬编码账号、密码、密钥、法规限重或固定重量。
- 核心业务规则放在应用/领域服务中，不放在路由或 ORM 事件中。
- `WeighingRecord` 与 `AuditLog` 采用追加式留痕。
- `COMPLETED` 任务普通用户不可修改，错误必须通过更正/冲正流程处理。
- 关键状态跳转、重量计算、复磅、幂等和并发场景必须有 pytest 测试。
- 未来 AI 只能通过受控应用服务查询或提交业务命令，不直接写数据库。

## 当前边界

Phase 1.1 已完成后端工程基础、配置、数据库会话、Alembic 环境和健康检查。业务模型、业务迁移、业务 API、前端应用、鉴权、地磅设备接入和 AI 能力均未实现。

## License

许可证尚未确定。在正式公开或接受外部贡献前补充 LICENSE 文件。
