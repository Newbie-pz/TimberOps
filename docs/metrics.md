# Application Metrics

TimberOps exposes Prometheus-compatible application metrics from the backend at
`GET /metrics`. Set `ENABLE_METRICS=true` to enable the endpoint. When disabled,
the same path returns `404` and does not reveal whether metrics are installed.

The endpoint is intentionally unauthenticated for Prometheus compatibility. In
production, the backend has no published host port; a Prometheus instance should
scrape `backend:8000/metrics` from the trusted Compose network. Do not proxy this
path through the public frontend or expose port 8000 to an untrusted network.

## Metric catalog

| Metric | Type | Labels | Meaning |
| --- | --- | --- | --- |
| `timberops_http_requests_total` | Counter | `method`, `path`, `status_code` | Completed HTTP requests |
| `timberops_http_request_duration_seconds` | Histogram | `method`, `path` | End-to-end HTTP latency |
| `timberops_ai_requests_total` | Counter | `provider`, `status` | AI requests by `success`, `client_error`, or `server_error` |
| `timberops_ai_latency_seconds` | Histogram | none | End-to-end AI endpoint latency |
| `timberops_billing_records_total` | Counter | `status` | Billing records entering `UNPAID`, `PAID`, or `WAIVED` |
| `timberops_billing_amount_total` | Histogram | none | CNY amount distribution for newly created billing records |
| `timberops_weighing_completed_total` | Counter | none | Successfully committed task completions |
| `timberops_db_pool_checked_out` | Gauge | none | Connections currently checked out across workers |
| `timberops_db_pool_size` | Gauge | none | Configured connection pool capacity across workers |

Business counters are event metrics. They start from the process/container
lifecycle and do not query or backfill historical database rows. Prometheus
handles counter resets across restarts. Billing and weighing events are recorded
only after their database transaction commits; idempotent billing operations do
not emit duplicate status transitions.

## Label and data safety

HTTP `path` uses the FastAPI route template, such as
`/api/v1/vehicles/{vehicle_id}`, rather than the requested URL. Unknown routes
use `__unmatched__`. Query strings and request bodies are never collected.

Metrics must not contain passwords, JWTs, authorization headers, user IDs,
usernames, license plates, customer data, AI prompts, responses, or token
content. Labels are deliberately limited to bounded operational dimensions.

## Prometheus integration

Example scrape configuration for a Prometheus container attached to the private
`timberops_prod_internal` network:

```yaml
scrape_configs:
  - job_name: timberops-backend
    scrape_interval: 15s
    static_configs:
      - targets: ["backend:8000"]
    metrics_path: /metrics
```

Production Uvicorn uses multiple workers. `docker-compose.prod.yml` configures
`PROMETHEUS_MULTIPROC_DIR`, and the backend entrypoint removes stale metric files
before starting a new container process. This directory is an internal runtime
detail and should not be shared between different backend containers.

Useful initial alerts include sustained 5xx growth, high request-latency
percentiles, AI error growth, and a checked-out connection count approaching the
pool capacity. Alert thresholds should be established from actual production
traffic rather than copied from development data.
