# TimberOps Frontend

TimberOps 磅房操作端，当前完成阶段为 **Phase 2.1 — Vue 3 Weighing Workbench**。前端只消费既有 FastAPI REST API，不承载称重规则，也不会自行改变任务状态。

## 技术栈

- Vue 3、TypeScript、Vite
- Vue Router、Pinia
- Axios
- Element Plus

## 环境要求

- Node.js 20.19+ 或 22.12+
- npm 10+
- TimberOps 后端默认运行在 `http://localhost:8000`

## 安装与启动

```bash
cd frontend
npm install
npm run dev
```

开发服务器默认监听 `http://localhost:5173`。Vite 会把 `/api` 请求代理到后端，因此本地开发时无需额外配置跨域。

生产构建：

```bash
npm run build
```

构建产物位于 `frontend/dist/`。

## API 配置

复制环境变量示例后按需调整：

```bash
cp .env.example .env
```

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api/v1` | Axios API 基础路径 |
| `VITE_DEV_PROXY_TARGET` | `http://localhost:8000` | 本地开发代理目标 |

生产环境可以把 `VITE_API_BASE_URL` 设置为完整的后端地址，或由反向代理继续提供 `/api/v1`。

## 页面

| 路径 | 页面 | 说明 |
| --- | --- | --- |
| `/` | Dashboard | 展示当日经营指标；后端暂无统计接口，当前明确使用 mock service |
| `/vehicles` | 车辆管理 | 查询、新增、编辑车辆档案 |
| `/customers` | 客户管理 | 查询、新增、编辑客户档案 |
| `/weighing/create` | 创建称重任务 | 选择车辆、客户和货物并创建出库称重任务 |
| `/weighing/workbench/:id` | 称重工作台 | 按后端状态推进空车、装货、重车、复磅和完成流程 |
| `/weighing/history` | 称重历史 | 筛选任务并查看称重记录详情 |

后端以 `weight_result=OVERWEIGHT` 表示超重。此时任务保持后端返回的 `WAIT_GROSS` 状态，工作台展示红色超重警示和复磅入口；前端没有新增 `OVERWEIGHT` 或 `REWEIGH` 状态。

## 目录结构

```text
src/
├── api/          # Axios 实例、错误处理和领域 API
├── components/   # 通用展示组件
├── layouts/      # 工业管理端主布局
├── router/       # 页面路由
├── stores/       # Pinia 跨页面状态
├── types/        # 与后端 Schema 对齐的 TypeScript 类型
├── utils/        # 时间、状态和吨位格式化
└── views/        # Dashboard、档案管理与称重页面
```

重量值按后端 Decimal 的 JSON 字符串处理；涉及净重和超重预览时采用千分之一吨的整数运算，避免 JavaScript 浮点误差。

## 当前不包含

- 登录、鉴权和权限管理
- AI、Agent、MCP、RAG
- 前端自动化测试套件
- Dashboard 真实统计接口
- Phase 2.2 及后续功能
