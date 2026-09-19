# TimberOps Frontend

TimberOps 前端是 Vue 3 单页应用，面向磅房操作、经营查询和系统管理。它复用统一 Axios Client、Pinia Auth Store、JWT Bearer 拦截器与 Element Plus，不维护第二套认证或权限状态。

## 技术栈与启动

Vue 3、TypeScript、Vite、Vue Router、Pinia、Axios、Element Plus。

```powershell
cd frontend
npm install
npm run dev

npm exec vue-tsc -- -b
npm run build
```

开发入口默认是 `http://localhost:5173`，`VITE_API_BASE_URL` 默认为 `/api/v1`。生产镜像由 Nginx 提供 SPA 文件并代理后端 API。

## Production build 策略

- 登录、注册、主 Layout 以及各业务页面均通过 Vue Router 动态导入；访问公开登录页不会预加载 AI、报表、审计、用户或费用页面。
- Element Plus 使用 Vite resolver 按组件和样式导入，中文 locale 由根级 `el-config-provider` 保持一致。
- 页面依赖随路由 chunk 加载，公共 Vue、Router、Pinia、Axios 和必要的 UI 运行时代码由 Vite 自动复用。
- 当前没有人工 `manualChunks`；按需导入后的 chunk 边界已经清晰，避免为了移动体积而制造相互依赖的 vendor 分块。
- Excel 文件由后端生成，前端只下载 Blob，因此不引入浏览器端 xlsx 库。

## 页面与路由

| 路由 | 页面 | 权限 |
| --- | --- | --- |
| `/login` | 登录 | 公开 |
| `/register` | 注册 | 入口由注册状态控制，后端最终校验 |
| `/pending-access` | 等待管理员分配角色 | 已登录无角色账号 |
| `/` | 真实数据运营 Dashboard | `dashboard:view` |
| `/vehicles` | 车辆管理 | `vehicle:view` |
| `/customers` | 客户管理 | `customer:view` |
| `/weighing/create` | 创建称重任务 | `weighing:create` |
| `/weighing/workbench/:id` | 称重工作台 | `weighing:view` |
| `/weighing/history` | 历史与导出 | `weighing:view` |
| `/billing` | 费用管理 | `billing:view` |
| `/audit` | 审计日志 | `audit:view` |
| `/reports` | 日/月经营报表 | `report:view` |
| `/users` | 用户与角色管理 | `user:manage` |
| `/ai` | 只读 AI 助手 | `ai:query` |

## Session 与权限

- Token 使用单一 localStorage key `timberops_access_token`，不保存密码或 password hash。
- Pinia Auth Store 保存当前用户、角色、权限和认证状态；刷新后调用身份 API 恢复会话。
- Axios 请求拦截器统一加入 Bearer Token；401 清理会话并跳转登录，403 保持登录并显示提示。
- 无角色账号进入 `/pending-access`，不会被自动授予角色。
- 菜单、路由和按钮使用 permission code 控制，不在组件中散落角色名判断。

前端权限控制仅用于体验；后端 RBAC 才是安全边界。localStorage Token 存在 XSS 风险，是当前 SPA 的已知限制。

## 业务交互与边界

- 称重工作台依据后端状态和权限开放皮重、待毛重、毛重、重复磅与完成操作。
- 删除请求不发送 operator id，操作人由 JWT 决定。
- Dashboard、Billing、Audit、Reports 均接入真实 API，不使用 mock service。
- AI Chat 使用独立 session id；AI 故障不影响核心业务页面。

当前没有自动化前端测试套件、离线模式、Refresh Token、SSO、多租户或真实磅秤设备 UI。发布前仍需 bundle 优化和人工角色矩阵 E2E。
