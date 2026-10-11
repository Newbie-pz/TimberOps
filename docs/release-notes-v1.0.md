# TimberOps v1.0.0 Release Notes

TimberOps v1.0.0 is the first code-release baseline of the vehicle weighing and operations platform. It is separate from certification of any particular public production deployment.

## Core business

- Vehicle and customer master data with lifecycle protection
- Manual tare, gross and overweight reweigh workflow with append-only readings
- Vehicle-type billing, payment/waiver handling, Dashboard, daily/monthly reports and Excel export
- Immutable completed-task reversal with ADMIN-only authorization and retained audit history

## Identity, security and reliability

- bcrypt passwords, JWT authentication and ADMIN/OPERATOR/VIEWER RBAC
- Bootstrap Admin, public-registration switch and operator identity auditing
- Safe API error envelopes, CORS and API-doc controls, secret scanning and hardened container defaults
- AI timeout/session isolation and PostgreSQL connection stability safeguards

## AI and integration

- Optional read-only LangGraph Agent with Doubao provider
- Five read-only AnalyticsService tools exposed through Streamable HTTP MCP
- Manual and Simulator weighbridge adapters behind a device integration interface

## Deployment and operations

- Development and production Docker Compose with Vue/Nginx and PostgreSQL 16
- Optional HTTPS/TLS edge overlay, health/readiness endpoints and Prometheus-compatible metrics
- Structured request logs, GitHub Actions quality gates, verified backup manifests and non-overwriting restore tooling

## Honest boundaries

This release does not include a vendor-specific physical weighbridge protocol, a trusted public CA deployment, remote MCP authentication, payment/refund processing, inventory, orders, SSO or multi-tenancy. A PAID weighing cannot be reversed until a real refund/funds-ledger workflow exists.
