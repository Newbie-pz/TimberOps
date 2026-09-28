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

Generate separate strong values for the PostgreSQL password and JWT signing key. Run the command twice and copy each result directly into the untracked `.env` file:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not reuse either value across environments. If a secret has appeared in Git history, chat, logs, screenshots, or support material, treat it as compromised and rotate it before deployment.

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

## Database backup and recovery

TimberOps provides manual wrappers around the PostgreSQL 16 `pg_dump` and `pg_restore` binaries already present in the database container. The host needs Docker Compose and Python, but does not need a separate PostgreSQL client installation.

Create a custom-format backup from the production Compose database:

```powershell
python scripts/backup_db.py
```

The command validates the Alembic revision and required tables before writing `backups/timberops_<UTC timestamp>.dump`. It writes through a temporary partial file, rejects empty output, and creates a sidecar JSON manifest containing the revision, size, and SHA-256 digest. Neither the archive nor manifest contains configuration metadata such as a password or database URL, although the archive itself contains business data and must be protected accordingly.

Copy completed backups to access-controlled storage outside the application host. A practical starting policy is daily backups, weekly retained backups, and an additional backup immediately before each release or migration. These are operational recommendations; TimberOps does not currently schedule, upload, or delete backups automatically.

Restore always requires an explicit backup file, a new database name, and the confirmation flag:

```powershell
python scripts/restore_db.py backups/timberops_20260928T090807Z.dump `
  --target-database timberops_restore_20260928 `
  --confirm-restore
```

The restore tool refuses the container's configured database and any database that already exists. It validates the archive and optional manifest before creating the target, restores without owners or privileges, then verifies the Alembic revision plus the `users`, `vehicles`, `customers`, `weighing_tasks`, `weighing_records`, `billing_records`, and `audit_logs` tables and their row counts. It never drops or overwrites the configured source database. A failed target is retained for diagnosis and must be removed manually after its exact identity has been reviewed.

For a machine-migration or disaster-recovery drill, start a separate PostgreSQL 16 container and pass `--container <name>` to both tools. After validation, deliberately update the database name in `DATABASE_URL_DOCKER` and restart application services; the script never performs this cutover automatically. Verify application `/ready`, authentication, representative weighing history, billing, and audit records before accepting the restored database.

The repository baseline has been exercised against two isolated PostgreSQL 16 containers; see the [Phase 2.8.1 recovery drill record](recovery-drill.md). Every deployment must still run and document its own restore drill because host storage, archive custody, data volume, and recovery-time requirements differ.

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

Use the detailed [release readiness checklist](release-checklist.md). HTTPS/TLS remains a release blocker for internet-facing deployment. Remote MCP also remains blocked until authentication, TLS, and network controls are implemented.
