# TimberOps v1.0 release readiness checklist

Use this checklist for the exact release artifact and deployment environment. A checked item records an operator decision or observed result; it does not imply the repository automates that control.

## Environment

- [ ] `APP_ENV=production`
- [ ] `DEBUG=false`
- [ ] Unique, strong `POSTGRES_PASSWORD` generated outside the repository
- [ ] Unique `JWT_SECRET_KEY` of at least 32 characters
- [ ] `.env` is present only on the deployment host and is not tracked by Git
- [ ] `DATABASE_URL_DOCKER` uses hostname `db` and matches the configured database credentials
- [ ] `AI_ENABLED=false`, or a valid `DOUBAO_API_KEY` is configured outside Git

## Security

- [ ] `PUBLIC_REGISTRATION_ENABLED` matches the approved registration policy
- [ ] `ENABLE_API_DOCS=false`
- [ ] `CORS_ALLOWED_ORIGINS` is empty for same-origin deployment or contains only exact HTTPS origins
- [ ] MCP remains bound to `127.0.0.1`, unless separate authentication, TLS, and network ACLs are in place
- [ ] Public hostname is confirmed
- [ ] Trusted TLS certificate is installed (a self-signed drill certificate does not satisfy this item)
- [ ] TLS private key access is restricted and its rotation owner is known
- [ ] HTTP redirects to HTTPS while preserving path and query
- [ ] TLS 1.2 and TLS 1.3 are enabled; obsolete protocol negotiation fails
- [ ] HSTS scope and max age are reviewed for the real hostname
- [ ] Any configured CORS origin uses the exact production HTTPS origin
- [ ] Backend port 8000 is not publicly exposed
- [ ] PostgreSQL port 5432 is not publicly exposed
- [ ] `/metrics` is not available through the public Nginx edge
- [ ] API documentation remains disabled in production
- [ ] MCP remains loopback/private unless separately authenticated and protected
- [ ] `python scripts/security_check.py` passes

## Database

- [ ] `alembic upgrade head` succeeds
- [ ] `alembic check` reports no pending schema operations
- [ ] A pre-release `pg_dump` custom-format backup completed and its manifest is retained
- [ ] Backup archive was copied to an access-controlled off-host location
- [ ] Restore into a new isolated PostgreSQL 16 database completed
- [ ] Restored Alembic revision, required tables, row counts, and representative relationships were verified
- [ ] The recovery operator and recovery-time expectation are documented

## Application

- [ ] Backend pytest suite passes
- [ ] Backend coverage report was reviewed
- [ ] Ruff passes
- [ ] Frontend `npm ci` and production build pass
- [ ] GitHub Actions is green for the release commit
- [ ] `/health` returns success
- [ ] `/ready` returns success against the intended database
- [ ] `/metrics` is disabled or reachable only from an internal monitoring network

## Operations

- [ ] Backend, frontend, MCP, PostgreSQL, and reverse-proxy logs were reviewed
- [ ] Backup storage location and retention owner are confirmed
- [ ] The documented recovery command was tested by the responsible operator
- [ ] Monitoring and escalation contacts are recorded outside the repository
- [ ] Rollback and restored-database cutover decisions are documented

## Explicit remaining blockers

- A real public hostname and trusted CA certificate are not supplied by this repository.
- The MCP server has no application-layer authentication and must remain loopback/private.
- Real weighbridge hardware integration and its failure handling have not been implemented.
