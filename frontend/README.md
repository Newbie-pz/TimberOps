# TimberOps Frontend

TimberOps 磅房操作端，当前完成阶段为 **Phase 2.5 — AI Reliability & Observability**。前端消费既有 FastAPI REST API，不承载称重规则、Agent 逻辑或数据库查询。

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
| `VITE_AI_TIMEOUT_MS` | `35000` | 仅 AI 问答使用的浏览器超时 |

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
| `/ai` | 智能助手 | 通过现有 LangGraph Agent 查询真实称重业务数据 |

后端以 `weight_result=OVERWEIGHT` 表示超重。此时任务保持后端返回的 `WAIT_GROSS` 状态，工作台展示红色超重警示和复磅入口；前端没有新增 `OVERWEIGHT` 或 `REWEIGH` 状态。

## AI 智能助手

AI 页面调用链：

```text
Vue /ai
  ↓ POST /api/v1/ai/chat
FastAPI
  ↓
LangGraph Agent / Doubao
  ↓
Read-only Business Tools
  ↓
AnalyticsService / PostgreSQL
```

页面支持自然语言提问、推荐问题、Tool Call 名称/参数/状态展示、请求防重复、清空当前对话和 AI 不可用提示。对话仅保存在当前页面内存，刷新后清空，不使用 `localStorage` 保存业务问答。

AI 问答默认使用 35 秒专用超时，略大于后端默认 30 秒的 Agent 总截止时间；普通业务 API 继续使用 15 秒全局超时。前端不会自动重试模型请求，失败后保留原问题供用户手动重试。页面分别为 503、504、502、500 的稳定 AI 错误码显示安全中文提示，不显示 Axios、SDK 或堆栈原文。

前端只显示后端明确返回的 `answer` 和 `tool_calls`，不显示或构造模型推理过程。当前助手严格只读，不会修改称重、车辆或客户数据。

MCP Server 是供外部 Agent 使用的独立协议入口，不参与 Vue 智能助手调用链；浏览器始终通过 `/api/v1/ai/chat` 访问 TimberOps Agent，也不会直接访问豆包 API。

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
└── views/        # Dashboard、档案管理、称重与 AI 助手页面
```

重量值按后端 Decimal 的 JSON 字符串处理；涉及净重和超重预览时采用千分之一吨的整数运算，避免 JavaScript 浮点误差。

## 当前不包含

- 登录、鉴权和权限管理
- AI 流式响应、后端对话持久化
- Multi-Agent、RAG、Web Search
- 前端 MCP Client
- 前端自动化测试套件
- Dashboard 真实统计接口
