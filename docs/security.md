# Production security baseline

This document describes the Phase 2.7.2 security baseline. It does not replace host, network, TLS, backup, or incident-response controls.

## Secrets

- Keep real values only in the untracked `.env` file or a deployment secret store. Never put them in Dockerfiles, Compose YAML, frontend build variables, screenshots, or support logs.
- Use a unique random `JWT_SECRET_KEY` of at least 32 characters. The backend rejects known placeholder prefixes even when they are long enough.
- Replace the example PostgreSQL password and URL-encode special characters when embedding it in a SQLAlchemy URL.
- Set a Doubao key only when `AI_ENABLED=true`. The key is injected into the backend process and is never exposed to the Vue build.
- Run `python scripts/security_check.py` before deployment. Its output identifies the category and location of a finding without printing the matched secret.
- Generate `POSTGRES_PASSWORD` and `JWT_SECRET_KEY` independently with a cryptographically secure generator such as `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- If a secret appears in Git, chat, logs, screenshots, or support material, consider it compromised and rotate it. Deleting the visible copy is not sufficient.
- HTTP request logs contain metadata only. They exclude headers, tokens, bodies, query strings, credentials, prompts, and AI responses.

Database archives contain business and identity data even when they contain no configuration secrets. Store them outside the repository with restricted access and encryption appropriate to the deployment. `backups/`, `*.dump`, and `*.sql` are ignored, and the security check rejects tracked database exports. Never inspect or print archive contents in CI logs.

TLS private keys follow the same rule: keep them in an untracked host directory with restrictive permissions. Root `certs/`, `*.key`, `privkey*.pem`, and `fullchain*.pem` deployment files are ignored. The security check fails when a private key or deployment certificate directory is tracked, but does not classify an explicitly located public test-certificate fixture as a secret. Rotate a private key if it is ever exposed.

## JWT policy

TimberOps uses short-lived HS256 access tokens. Tokens contain `sub`, `username`, `jti`, `iat`, and `exp`; all claims, the signature, algorithm, timestamps, UUIDs, and non-empty username are validated. The default lifetime is 60 minutes.

There is no refresh token or server-side revocation list in this phase. Disabling a user takes effect immediately because every authenticated request reloads the active user from the database. Other issued tokens remain usable until expiry unless the signing key is rotated. Rotating the JWT key signs out every client.

The SPA currently stores its bearer token in `localStorage`. HTTPS protects the token in transit but does not remove its XSS exposure. Avoid untrusted HTML rendering and third-party scripts. HttpOnly `Secure` `SameSite` cookie sessions, MFA, and centralized token revocation remain future hardening options and require a separate authentication design.

## Registration

Keep `PUBLIC_REGISTRATION_ENABLED=false` in production unless anonymous account creation is explicitly intended. The backend remains the security boundary and returns `REGISTRATION_DISABLED` when registration is disabled; hiding the frontend link is only a usability measure. Registration never assigns a role. The first administrator is created through the existing interactive bootstrap command.

## CORS and API documentation

The Nginx deployment uses relative `/api` URLs, so normal production traffic is same-origin and `CORS_ALLOWED_ORIGINS` can stay empty. If the frontend is hosted separately, configure only its exact HTTPS origin or origins as a comma-separated value. Wildcard origins are rejected and credentialed CORS is disabled.

Set `ENABLE_API_DOCS=false` in production. Development can enable `/docs`, `/redoc`, and `/openapi.json` without removing those capabilities from the codebase. Production unhandled errors use a stable JSON envelope and never return exception text, SQL detail, traceback, or filesystem paths.

## Authorization

Authentication resolves an active user on every request. Backend RBAC is the enforcement boundary; frontend menu and button visibility is not considered authorization. Vehicle, customer, weighing, billing, audit, report, export, AI, dashboard, and user-management endpoints use their existing Permission Catalog codes. Permission denial consistently returns HTTP 403 with `PERMISSION_DENIED`.

## Docker deployment

- PostgreSQL and FastAPI have no host port mapping in production Compose.
- PostgreSQL is reachable only as `db` on the internal Compose network. Production settings reject loopback database hosts.
- MCP runs separately and binds to host loopback by default. Expose it remotely only behind appropriate firewall and authentication/network controls.
- The backend image runs as the non-root `timberops` user, and Docker build contexts exclude `.env`, virtual environments, caches, and Git metadata.
- The optional TLS overlay terminates TLS at Nginx, redirects HTTP to HTTPS, and supports TLS 1.2/1.3. HSTS uses a conservative one-day max age only on HTTPS responses, without `includeSubDomains` or `preload`.
- Nginx overwrites client forwarding headers. Production Uvicorn accepts forwarded scheme/client metadata from the Compose network so HTTPS redirects are correct; this is safe only while backend port 8000 remains unexposed. Request logging additionally accepts `X-Real-IP` only when its direct peer is on a loopback/private network.
- `/metrics` and production API documentation are explicitly blocked at the public Nginx edge. MCP remains a separate loopback-only endpoint.

Content-Security-Policy is intentionally deferred until Vue, Element Plus, dynamic chunks, and any required inline styling have been measured in enforcement/report-only mode. The project does not add `unsafe-eval` merely to satisfy a checklist.

## Known limitations and release blockers

- The SPA stores its access token in localStorage, so an XSS vulnerability could expose it.
- JWTs have no server-side revocation list; key rotation invalidates all tokens, while ordinary tokens otherwise expire naturally.
- The MCP server has no application-layer authentication for remote clients and must remain loopback/private until protected.
- HTTPS deployment is supported, but the repository does not provide a public hostname or trusted CA certificate.
- A default, example, reused, or weak PostgreSQL password is a release blocker, even when the database has no published port.
- Manual backup and non-overwriting restore tools are available, but scheduling, off-host encrypted storage, retention enforcement, and incident-response ownership remain deployment responsibilities.
