# Engineering quality and CI

TimberOps 使用 GitHub Actions 持续集成验证代码质量和可构建性。当前只有 CI，没有自动部署、镜像发布或 CD。

## CI triggers and permissions

`.github/workflows/ci.yml` 在以下事件运行：

- push 到 `main`
- 面向 `main` 的 pull request

Workflow 仅授予 `contents: read`，同一分支的新运行会取消旧运行。CI 不依赖 GitHub Secrets，不连接外部数据库或 AI Provider。

## Jobs

### Backend Quality

- Python 3.12 与 pip cache
- 安装 `backend/requirements-dev.txt`
- `ruff check` 检查后端和 security check 脚本
- 运行全部 pytest，并输出 `pytest-cov` statement coverage
- 使用 SQLite in-memory；`AI_ENABLED=false`

当前稳定本地基线为 2835 statements、141 missing、总 coverage 95%。首版 CI 仍不设置 `fail-under`：先观察不同平台和后续变更中的稳定性，再基于历史数据制定阈值，避免用一次测量鼓励无意义测试。

### Frontend Quality

- Node.js 22 与 npm cache
- 只使用 `npm ci` 和 `package-lock.json`
- `npm run build` 先执行 `npm run typecheck`，随后执行 Vite production build

### Migration Check

- 启动隔离的 PostgreSQL 16 service
- 使用明确标识的 CI-only 用户名和密码
- 从空数据库执行 `alembic upgrade head`
- 执行 `alembic check`，检查 ORM 与 migration head 的差异

### Configuration and Docker Build

- 在没有真实 `.env` 的环境执行 `scripts/security_check.py`
- 使用 CI-only placeholder 验证开发和生产 Compose 配置
- 构建 backend 与 frontend Dockerfile
- 不启动完整 Compose、不推送镜像

## Local commands

Backend：

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m ruff check . ..\scripts\security_check.py
python -m pytest
python -m pytest --cov=app --cov-report=term-missing
```

Frontend：

```powershell
cd frontend
npm ci
npm run typecheck
npm run build
```

Repository / PostgreSQL：

```powershell
python scripts/security_check.py
docker compose config --quiet
docker compose -f docker-compose.prod.yml config --quiet

cd backend
python -m alembic upgrade head
python -m alembic check
```

Docker image verification：

```powershell
docker build -t timberops-backend:local backend
docker build -t timberops-frontend:local frontend
```

## Frontend test assessment

前端当前没有 Vitest 套件。Auth Store、Axios interceptor 和 Router Guard 与 localStorage、路由实例及 Element Plus 消息服务耦合，首轮 CI 通过 TypeScript 与 production build 获得稳定信号。本阶段不为测试数量引入脆弱 DOM 测试；后续可先提取 permission 和错误映射纯函数，再针对这些稳定边界增加 Vitest。

## Remote verification

本地只能验证 workflow YAML 和其中的命令。首次 push 后仍需在 GitHub Actions 确认四个 job 都在 hosted runner 成功，再决定是否添加 CI badge 或配置分支保护。
