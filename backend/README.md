# TimberOps Backend

TimberOps 后端负责提供 HTTP API、应用配置、数据库访问基础设施，以及后续称重、订单和库存领域能力。当前仅完成 Phase 1.1 Backend Foundation，不包含业务模型或业务接口。

## 技术栈

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- Pydantic v2 与 pydantic-settings
- Alembic
- PostgreSQL（psycopg 3）
- pytest

## 目录结构

```text
backend/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── api/
│   │   └── router.py        # 顶层 APIRouter 与健康检查
│   ├── core/
│   │   └── config.py        # 环境变量配置
│   ├── db/
│   │   ├── base.py          # SQLAlchemy DeclarativeBase
│   │   └── session.py       # Engine、SessionLocal、get_db
│   ├── models/              # Phase 1.2 业务模型入口
│   ├── schemas/             # Pydantic 模型
│   ├── services/            # 应用服务
│   └── integrations/ai/     # 仅预留边界，当前无 AI 实现
├── migrations/
│   ├── env.py               # Alembic 环境
│   └── versions/            # 数据库版本脚本
├── tests/
│   └── test_health.py
├── alembic.ini
├── requirements.txt
└── Dockerfile
```

## 配置

配置通过系统环境变量或 `.env` 加载。后端从当前目录的 `.env` 或项目根目录的 `.env` 读取：

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/timberops
APP_NAME=TimberOps backend
DEBUG=false
```

不要提交真实密码。项目根目录已提供 `.env.example`。

健康检查不访问数据库；使用数据库或 Alembic 时必须提供 `DATABASE_URL`。

## 本地启动

在项目根目录创建 `.env` 后：

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

访问：

- 健康检查：`http://localhost:8000/health`
- OpenAPI：`http://localhost:8000/docs`

运行测试：

```powershell
python -m pytest
```

运行 Alembic：

```powershell
python -m alembic current
python -m alembic upgrade head
```

当前没有业务迁移，因此 `versions` 目录为空。

## Docker 启动

先构建后端镜像：

```powershell
docker build -t timberops-backend .\backend
```

运行时通过环境文件提供配置；容器内连接根 Compose 的数据库时，应使用可解析的数据库主机名，而不是 `localhost`：

```powershell
docker run --rm -p 8000:8000 --env-file .env timberops-backend
```

Phase 1.1 按要求未把后端服务加入根目录 `docker-compose.yml`。在后续 Compose 集成前，上述容器命令要求 `.env` 中的数据库地址可从容器访问；健康检查本身不连接数据库。

## 当前实现范围

已完成：

- FastAPI 应用工厂和统一 APIRouter
- `GET /health`
- pydantic-settings 配置
- SQLAlchemy Engine、SessionLocal 和请求依赖
- Alembic 基础环境及空 metadata
- Dockerfile
- 健康检查测试

未实现：称重、车辆、客户、用户、认证、订单、库存、业务表、AI、Agent、MCP、RAG 和设备接入。
