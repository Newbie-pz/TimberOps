# Production deployment

TimberOps can run as four Docker Compose services: PostgreSQL, FastAPI, Nginx/Vue, and the standalone read-only MCP server. The existing `docker-compose.yml` remains the development-only PostgreSQL stack.

## Prerequisites

- Docker Engine with Docker Compose v2
- Free host ports `8080` (web) and `8001` (MCP), or alternative values in `.env`
- At least 32 random characters for the JWT signing secret

## Configure the environment

Copy `.env.example` to `.env` and replace every placeholder before deployment. In particular, set `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, and both database URLs consistently. `DATABASE_URL` is for local development and normally uses `localhost`; `DATABASE_URL_DOCKER` is injected only into production containers and must use the Compose hostname `db`.

If a database password contains URL-significant characters, URL-encode it in `DATABASE_URL_DOCKER`. Keep `PUBLIC_REGISTRATION_ENABLED=false` unless public self-registration is explicitly required. AI and Doubao values remain optional when `AI_ENABLED=false`; real API keys must only be stored in the untracked `.env` file or a deployment secret store.

## Build and start

```powershell
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

Open `http://localhost:8080`. Only Nginx is publicly exposed by default. The backend and database are available only on the internal Compose network.

The MCP Streamable HTTP endpoint is `http://127.0.0.1:8001/mcp` by default. This loopback binding is intentional. Set `MCP_BIND_ADDRESS=0.0.0.0` only when an external client must connect and network access is protected separately.

## Bootstrap the first administrator

After the containers are healthy, run the existing interactive bootstrap command:

```powershell
docker compose -f docker-compose.prod.yml exec backend python -m app.cli.bootstrap_admin
```

The command does not accept a password argument and refuses to create another bootstrap administrator after an ADMIN already exists.

## Database migrations

The single backend container runs `alembic upgrade head` before starting Uvicorn. If migration fails, the backend exits and dependent services do not start. The MCP service waits for the healthy backend and does not run migrations, which prevents concurrent migration attempts in this single-backend deployment.

## Logs

```powershell
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f mcp
docker compose -f docker-compose.prod.yml logs -f db
```

FastAPI, MCP, and Nginx logs are written to container stdout/stderr.

## Stop and persistence

```powershell
docker compose -f docker-compose.prod.yml down
```

PostgreSQL data is stored in the named `postgres_prod_data` volume and survives `down` and subsequent starts. Only `docker compose -f docker-compose.prod.yml down -v` removes that production data volume; do not use `-v` unless permanent deletion is intended.

## Development mode

The original workflow is unchanged:

```powershell
docker compose up -d
cd backend
python -m uvicorn app.main:app --reload
cd ../frontend
npm run dev
```
