# TimberOps 系统架构设计

## 1. 架构目标与边界

TimberOps 首期服务中小型木材加工企业，但磅房是可独立运行的通用车辆称重模块，可处理矿石、煤炭、木材及其他货物。订单和库存是可选的企业内部业务关联，不是创建或完成称重任务的前置条件。

系统采用模块化单体，以较低部署成本获得清晰边界和可靠事务。设计原则：

- 后端是状态、重量计算和权限校验的可信边界。
- 称重、订单、库存各自管理本域事实，不通过隐式副作用耦合。
- 历史读数追加保存，任务表只维护最新有效汇总。
- 关键命令具备事务、并发控制、幂等和审计能力。
- AI、MCP 与设备协议置于外围适配层，不进入核心领域。

## 2. 总体架构

```text
┌──────────────────────────────────┐
│ Vue 3 Web（磅房端 / 运营端）     │
└────────────────┬─────────────────┘
                 │ HTTPS / JSON API
┌────────────────▼────────────────────────────────────┐
│ FastAPI 模块化单体                                  │
│                                                    │
│ API → 应用用例 → 领域规则 → Repository / ORM       │
│          │                                         │
│          ├─ Weighing（独立称重与磅单）              │
│          ├─ Orders（可选关联）                      │
│          ├─ Inventory（显式业务操作）               │
│          ├─ Vehicles / Customers / Identity        │
│          └─ Audit                                   │
└──────────────┬───────────────────┬─────────────────┘
               │                   │ adapter ports
        ┌──────▼──────┐    ┌──────▼─────────────────┐
        │ PostgreSQL  │    │ WeighbridgeAdapter     │
        └─────────────┘    │ V1: Manual             │
                           │ Future: Serial/Modbus   │
                           └────────────────────────┘

未来：AI 查询入口 → 受控查询应用服务 → 已授权的领域读模型
```

## 3. 分层职责

### API 层

负责版本化路由、请求验证、认证依赖、响应模型和 HTTP 错误映射。不得在路由中编写状态迁移、重量判定或库存逻辑。

### 应用层

以用例协调权限、事务与审计，例如创建称重任务、提交皮重、提交毛重、发起超重复磅、完成磅单。订单/库存关联必须通过独立且显式的业务用例执行；“完成称重”本身不修改订单或库存。

### 领域层

保存不依赖框架的称重状态机、吨位 Decimal 计算、超重判定、复磅规则和其他领域约束。领域规则应支持纯单元测试。

### 基础设施与适配器层

包含 SQLAlchemy、数据库会话、Alembic、日志及地磅设备适配器。核心服务依赖 `WeighbridgeAdapter` 抽象，不依赖串口或厂商 SDK。

## 4. 模块边界

| 模块 | 职责 |
| --- | --- |
| identity | 用户、角色、认证和权限 |
| customers | 可选客户主数据 |
| vehicles | 车辆、常用司机和核定总质量 |
| weighing | 独立称重任务、追加式读数、状态机、复磅与磅单 |
| materials | 企业内部木材物料主数据 |
| orders | 客户订单、订单明细、数量和订单状态 |
| inventory | 企业自身库存余额、入出库流水与冲正 |
| audit | 敏感操作的不可篡改审计查询 |
| integrations.ai | 未来 Agent/MCP/模型适配边界；当前不实现 |

`WeighingTask.vehicle_id` 必填，`customer_id` 与 `order_id` 可空。V1 的 `cargo_type` 固定为 `ORE / COAL / TIMBER / OTHER`，由前端下拉选择；`cargo_name` 可记录“铁矿石”“石料”等具体名称。称重使用自身货物字段，不依赖 Material。只有木材等明确属于内部业务的场景，才可选关联订单，并由后续显式用例决定是否形成订单履约或库存流水。

## 5. 称重状态与结果

两个维度必须彻底分离：

- `status`：`WAIT_TARE / TARE_COMPLETED / LOADING / WAIT_GROSS / GROSS_COMPLETED / COMPLETED / CANCELLED`
- `weight_result`：`PENDING / NORMAL / OVERWEIGHT`

第二次或后续复磅写入后，流程状态均为 `GROSS_COMPLETED`，系统同时计算结果。只有 `weight_result=NORMAL` 才能进入 `COMPLETED`。超重时通过“卸货后重新称重”命令返回 `WAIT_GROSS`，不得存在 `status=OVERWEIGHT`，也不得授权直接超重完成。

取消是流程终态，但不会抹除已经产生的称重结果和读数。取消需要权限与原因；`COMPLETED` 不得转为 `CANCELLED`。

## 6. 数据一致性

- 核心称重统一为吨，Python 使用 `Decimal`，PostgreSQL 使用 `NUMERIC(10, 3)`。
- 任务创建时复制车辆的 `allowed_gross_weight_tons`，不在历史查询时回读当前车辆限重。
- 所有实际读数先追加到 `WeighingRecord`；任务表的重量字段是最新有效值汇总。
- 毛重或复磅必须大于皮重，失败时不更新汇总结果。
- 提交读数时锁定任务行或校验 `version`，避免并发覆盖。
- 客户端关键命令携带幂等键，网络重试不得重复插入记录。
- 保存读数、更新汇总、计算结果和写审计日志必须处于同一数据库事务。
- 称重完成不自动更新订单或库存。需要关联时由另一个显式、幂等、可审计的应用用例处理。

## 7. 地磅适配扩展点

V1 只实现人工录入，记录来源为 `MANUAL`。未来设备接入保持以下边界：

```text
WeighbridgeAdapter
├── ManualWeighbridgeAdapter
├── MockWeighbridgeAdapter
├── SerialWeighbridgeAdapter
└── ModbusWeighbridgeAdapter
```

RS-232、RS-485、串口、Modbus 或厂商私有协议的读取、稳定值判定与 kg→t 转换均由适配器负责。核心领域只接收以吨为单位的 Decimal 和标准化元数据。Phase 0.1 不实现上述代码。

## 8. 权限与审计

初期建议 RBAC：`ADMIN`、`OPERATOR`、`WEIGHER`、`AUDITOR`。

- 普通用户不得直接修改 `COMPLETED` 任务。
- 已保存的 `WeighingRecord` 不得更新或删除。
- 错误通过更正/冲正记录表达，保留原始事实和原因。
- 所有人工更改均写 `AuditLog`，至少包含操作者、动作、目标、前后值、原因和时间。
- 超重车辆不得由任何 V1 角色直接完成，必须复磅为正常。

## 9. 前端磅房页面规划

### 创建任务

包含车牌号、司机信息、货物类型下拉框、货物名称、客户（可选）、关联订单（可选）、车辆核定总质量快照和备注。选择订单时需校验客户一致性，但未选择订单不阻塞称重。

### 第一次称重

展示空车重量（t）、称重时间和操作员。V1 由操作员人工输入，前端仅做格式提示，后端再次校验。

### 第二次称重与复磅

展示重车重量（t），自动预览净货重、剩余载重和超重结果。后端结果为准：正常使用绿色 `NORMAL`，超重使用红色 `OVERWEIGHT`，并明确提示“禁止完成出厂，需要卸货并重新称重”。

### 历史与磅单

按顺序展示第一次皮重、第一次毛重、所有复磅记录、最终有效毛重、最终净重、最终结果和操作人员，不用任务汇总字段替代完整历史。

## 10. API 与时间约定

- API 路径使用 `/api/v1`。
- Pydantic 请求/响应模型与 ORM 模型分离。
- 时间以带时区 UTC 存储，前端按用户时区展示。
- 核心字段以 `_tons` 后缀明确单位，API 示例固定显示三位小数。
- 创建和称重命令支持幂等请求标识。
- 服务端计算净重、剩余载重和超重值，不接受客户端覆盖计算结果。

## 11. AI 与 MCP 扩展边界

当前不引入 LangChain、LangGraph、MCP、模型 API、RAG 或多 Agent。未来可在独立查询应用服务上提供受控能力，例如：

- `query_weighing_task`
- `query_weighing_history`
- `query_today_weighing_records`
- `query_overweight_records`
- `get_today_total_net_weight`
- `query_vehicle_history`

这些名称只是未来用例候选，不是本阶段 API 或工具实现。AI 只能访问授权后的只读模型；写操作必须复用既有应用服务、权限、校验和审计，禁止直连数据库。

## 12. 部署演进

Phase 0.1 的 Compose 仍只启动 PostgreSQL，无需增加服务。Phase 1 建立可运行后端、前端与迁移后再加入对应镜像。生产环境还需 TLS、托管密钥、备份恢复、结构化日志和监控。
