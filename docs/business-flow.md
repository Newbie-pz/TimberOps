# TimberOps 业务流程设计

## 1. V1 业务范围

磅房作为独立模块，V1 处理以下统一流程：

```text
空车进厂
  → 创建任务并选择货物类型
  → 称空车皮重
  → 装载货物
  → 称重车毛重
  → 计算净重与超重值
  → 正常：完成并生成磅单
  → 超重：卸货、追加复磅，直至正常后完成
```

支持 `ORE / COAL / TIMBER / OTHER`。车辆必选，客户和订单可选。无订单的矿石、煤炭或其他货物车辆可以走完整流程，不触发 TimberOps 内部库存。

V1 的 `weighing_direction` 默认为 `OUTBOUND`，暂不实现“重车进厂、卸货后称空车”的 `INBOUND` 反向流程。

## 2. 创建任务

必填：

- 车辆 `vehicle_id`
- 货物类型 `cargo_type`

可选：

- 客户 `customer_id`
- 内部订单 `order_id`
- 货物名称 `cargo_name`
- 货物备注 `cargo_remark`

`cargo_type` 必须通过枚举选择，不接受自由文本类型。`cargo_name` 用于“铁矿石”“石料”等具体名称；选择 `OTHER` 时建议设为必填。

创建时从车辆档案复制 `allowed_gross_weight_tons`，并保存当次司机快照：

```text
status = WAIT_TARE
weight_result = PENDING
weighing_direction = OUTBOUND
```

## 3. 状态机

| 当前状态 | 允许动作 | 下一状态 | 结果变化 |
| --- | --- | --- | --- |
| WAIT_TARE | 提交首次空车重量 | TARE_COMPLETED | 保持 PENDING |
| TARE_COMPLETED | 确认开始装载 | LOADING | 保持 PENDING |
| LOADING | 确认装载完成 | WAIT_GROSS | 保持 PENDING |
| WAIT_GROSS | 提交首次毛重或复磅 | GROSS_COMPLETED | 系统计算 NORMAL/OVERWEIGHT |
| GROSS_COMPLETED + NORMAL | 完成出厂 | COMPLETED | 保持 NORMAL |
| GROSS_COMPLETED + OVERWEIGHT | 确认卸货复磅 | WAIT_GROSS | 暂时保留 OVERWEIGHT |
| 非终态 | 授权取消并填写原因 | CANCELLED | 保留已有结果 |
| COMPLETED / CANCELLED | 普通业务动作 | 禁止 | 不变 |

禁止的设计与操作：

- 不存在 `status=NORMAL` 或 `status=OVERWEIGHT`。
- `WAIT_TARE` 不能提交毛重。
- 客户端不能指定 `net_weight_tons`、`overweight_tons` 或 `weight_result`。
- `weight_result=OVERWEIGHT` 不能进入 `COMPLETED`。
- 不能用取消或管理员放行绕过超重复磅。
- 已完成任务普通用户不能直接修改。

## 4. 读数与计算

每次真实读数必须先追加一条 `WeighingRecord`，再更新任务汇总。所有值使用吨和三位小数：

```text
net_weight_tons = gross_weight_tons - tare_weight_tons
remaining_capacity_tons = allowed_gross_weight_tons - gross_weight_tons
overweight_tons = max(-remaining_capacity_tons, 0)

if gross_weight_tons <= allowed_gross_weight_tons:
    weight_result = NORMAL
else:
    weight_result = OVERWEIGHT
```

`remaining_capacity_tons` 可为负数，负值的绝对值等于超重吨数；它是计算展示值，不必在 V1 数据库持久化。

校验规则：

- 皮重、毛重、复磅均必须大于 0。
- 毛重或复磅必须大于有效皮重。
- 数据库使用 `NUMERIC(10,3)`，Python 使用 `Decimal`，禁止 float。
- 服务端负责量化到三位小数并计算，前端预览不能替代后端结果。
- 称重时间和操作员来自可信服务端上下文。

## 5. WeighingRecord 追加规则

示例：

| sequence_no | weight_type | weight_tons | source | 含义 |
| --- | --- | --- | --- | --- |
| 1 | TARE | 15.820 | MANUAL | 首次空车重量 |
| 2 | GROSS | 50.200 | MANUAL | 首次重车重量，判定超重 |
| 3 | REWEIGH | 48.600 | MANUAL | 卸货后重新称重，判定正常 |

- `sequence_no` 在任务内严格递增。
- 首次重车使用 `GROSS`，后续重称全部使用 `REWEIGH`。
- 不覆盖或删除 50.200 t 的超重记录。
- 任务的 `gross_weight_tons/gross_time` 更新为最新有效读数，历史页面仍从全部记录还原过程。
- V1 来源只创建 `MANUAL`；枚举同时预留 `DEVICE`。

## 6. 超重闭环

假设核定总质量为 49.000 t，首次毛重为 50.200 t：

```text
status = GROSS_COMPLETED
weight_result = OVERWEIGHT
overweight_tons = 1.200
```

此时“完成出厂”按钮不可用，并显示“禁止完成出厂，需要卸货并重新称重”。操作员确认开始复磅后，任务返回 `WAIT_GROSS`；卸货后追加 `REWEIGH`。若新读数为 48.600 t：

```text
status = GROSS_COMPLETED
weight_result = NORMAL
overweight_tons = 0.000
```

之后才可进入 `COMPLETED`。如果仍超重，则重复卸货与复磅，不限制历史记录数量。

## 7. 与客户、订单、库存的关系

### WeighingTask

负责车辆称重、净重计算、超重判断、磅单与运输历史。客户、订单均为可选关联。

### Order

负责客户业务订单、订单货物、业务数量与订单状态。关联称重任务不代表自动履约。

### Inventory

负责企业自身库存变化。称重净重不自动等于库存数量，尤其矿石、煤炭等可能只是借用磅房。

如内部木材订单需要引用称重结果，应由独立的“确认业务入/出库”用例明确选择任务、订单、物料和记账数量。该用例自行校验单位、幂等与权限；称重完成本身不创建库存流水。

## 8. 人工录入与设备接入

Phase 1 和 Phase 2 使用人工录入。未来 `WeighbridgeAdapter` 可接入 Mock、串口、Modbus 或厂商协议。若设备返回 kg，适配器负责转换为吨；状态机和计算层不感知设备协议。

## 9. 审计与纠错

- `COMPLETED` 任务普通用户不可修改。
- `WeighingRecord` 保存后不可覆盖或删除。
- 错误必须通过新增更正/冲正记录处理，原始事实永久保留。
- 所有人工更改记录 `AuditLog`：`operator_id`、`action`、`target_type`、`target_id`、`before_value`、`after_value`、`reason`、`created_at`。
- 提交读数、更新任务汇总、计算结果和写审计必须在一个事务中完成。

具体的称重记录更正状态和磅单作废/重开流程需在实现前由业务方确认，Phase 0.1 不实现。

## 10. 前端交互

- 创建页：车牌号、司机、货物类型下拉框、货物名称、客户（可选）、订单（可选）、核定总质量和备注。
- 首次称重页：空车重量、称重时间、操作员。
- 第二次/复磅页：重车重量、净货重、剩余载重、超重吨数和判定结果。
- `NORMAL` 使用绿色；`OVERWEIGHT` 使用红色并阻断完成操作。
- 历史页：第一次皮重、第一次毛重、全部复磅、最终有效重量和最终净重。

## 11. 磅单最小内容

任务号、方向、车牌号、当次司机、货物类型、货物名称、可选客户/订单、核定总质量、皮重、最终毛重、最终净重、超重值、最终结果、全部称重时间、操作员和完成时间。磅单应能关联完整称重历史，不能只保留最后一次读数。
