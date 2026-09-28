# HTTPS/TLS integration drill record

This record documents the Phase 2.8.2 integration drill performed on 2026-09-28. It proves that the repository's optional TLS edge works; it does not represent a public deployment or a trusted certificate installation.

## Isolation

- Compose project: `timberops-phase282-drill`
- Certificate: one-day self-signed RSA certificate for `localhost`, generated only for the drill
- Published addresses: `127.0.0.1:28080` for HTTP and `127.0.0.1:28443` for HTTPS
- Database: dedicated project-scoped PostgreSQL 16 volume
- MCP: not started or exposed during the drill
- Existing TimberOps containers and volumes were not stopped or modified

## Verified behavior

- HTTP returned `308` and preserved `/login?next=%2Fbilling` in the HTTPS location.
- HTTPS `/`, `/login`, `/api/v1/auth/registration-status`, `/health`, and `/ready` returned `200`.
- `/ready` confirmed both database connectivity and migration revision.
- HTTPS responses included HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy`.
- The HTTP redirect did not include HSTS.
- Public `/metrics`, `/docs`, `/redoc`, and `/openapi.json` returned `404`.
- `backend:8000/metrics` remained reachable from the internal Docker network.
- A spoofed public `X-Real-IP`/`X-Forwarded-For` value did not reach the backend request log.
- A FastAPI trailing-slash redirect generated behind Nginx used an absolute `https://` location, confirming Uvicorn honored the trusted proxy scheme.
- TLS 1.2 and TLS 1.3 requests succeeded; TLS 1.0 negotiation failed.
- Nginx configuration validation succeeded.
- With certificate paths that did not contain valid certificate files, the frontend entered restart failure with exit code 1 and an explicit certificate-load error. It did not fall back to HTTP and did not print private-key content.

## Cleanup

The self-signed certificate, private key, test containers, networks, and database volumes were deleted after verification. The certificate was never added to Git and was never publicly trusted.

## Deployment reminder

For an internet-facing release, repeat the checks using the approved public hostname and a trusted CA certificate without `curl -k`. Confirm certificate renewal and private-key ownership before checking the production release checklist.
