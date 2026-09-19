# Production deployment

TimberOps can run as four Docker Compose services: PostgreSQL, FastAPI, Nginx/Vue, and the standalone read-only MCP server. The existing `docker-compose.yml` remains the development-only PostgreSQL stack.

## Prerequisites

- Docker Engine with Docker Compose v2
- Free host ports `8080` (web) and `8001` (MCP), or alternative values in `.env`
- At least 32 random characters for the JWT signing secret

## Configure the environment

Copy the template first:

```powershell
Copy-Item .env.example .env
```

Replace every placeholder before deployment. In particular, set `POSTGRES_PASSWORD`, `DATABASE_URL_DOCKER`, `JWT_SECRET_KEY`, and `FRONTEND_PORT`; AI settings are optional. `DATABASE_URL` is for local development and normally uses `localhost`; `DATABASE_URL_DOCKER` is injected only into production containers and must use the Compose hostname `db`.

If a database password contains URL-significant characters, URL-encode it in `DATABASE_URL_DOCKER`. Keep `PUBLIC_REGISTRATION_ENABLED=false` unless public self-registration is explicitly required. AI and Doubao values remain optional when `AI_ENABLED=false`; real API keys must only be stored in the untracked `.env` file or a deployment secret store.

Keep `ENABLE_API_DOCS=false` for production. The default Nginx deployment is same-origin, so `CORS_ALLOWED_ORIGINS` should normally remain empty. If the frontend is hosted on another origin, set an exact comma-separated HTTPS allowlist; wildcards are rejected.

Run the redacting preflight check before building:

```powershell
python scripts/security_check.py
```

## Build and start

```powershell
docker compose -f docker-compose.prod.yml config --quiet
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

## Health and readiness

The production backend container healthcheck calls `/ready`, not `/health`.
This prevents the frontend and MCP services from treating a backend with an
unavailable or migration-outdated database as ready for business traffic.

- `/health` returns `200` while the FastAPI process is alive, even if PostgreSQL
  is unavailable.
- `/ready` returns `200` only when PostgreSQL accepts `SELECT 1` and its Alembic
  revision matches the code head; otherwise it returns `503`.
- `/metrics` exposes Prometheus metrics only when `ENABLE_METRICS=true`.

These endpoints do not require JWT credentials and therefore expose only fixed
status categories. The backend remains private to the Compose network. Docker
healthchecks are useful process diagnostics but are not a replacement for a
platform-specific traffic readiness mechanism.

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

## Production / v1.0 checklist

These are release blockers or explicit deployment decisions, not completed capabilities:

- [ ] Replace the PostgreSQL placeholder with a strong unique password and keep both database settings consistent.
- [ ] Generate an environment-specific JWT secret of at least 32 random characters.
- [ ] Confirm the intended public registration policy; production defaults to disabled.
- [ ] Terminate HTTPS/TLS at a trusted reverse proxy or ingress.
- [ ] Implement, schedule, and restore-test PostgreSQL backups.
- [ ] Add authentication and network access control before exposing MCP remotely.
- [ ] Run tests, builds, Alembic check, Compose validation, and `scripts/security_check.py` for the release artifact.
