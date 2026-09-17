# HTTP request observability

Phase 2.7.3.1 adds a single structured request log for every FastAPI HTTP request and a correlation ID shared with the existing AI observability layer.

## Request ID lifecycle

The backend safely reuses an incoming `X-Request-ID` when it is 1–128 characters and contains only letters, numbers, `.`, `_`, `:`, or `-`. Invalid, missing, oversized, or control-character values are replaced with a UUID. The resolved value is stored in request state and returned in the `X-Request-ID` response header.

The unified middleware creates the ID before the AI middleware runs. AI lifecycle logs therefore use the same ID instead of generating a second correlation value.

## JSON fields

The `timberops.http` logger writes each compact JSON object directly to stdout as one line, containing:

- `event`: `http_request` or `slow_request`
- `timestamp`: request start time in UTC ISO 8601 format
- `request_id`
- `method`
- `path` without query parameters
- `status_code`
- `duration_ms`
- `user_id` and `username`, or `null` when no valid JWT is present
- `client_ip`

Normal responses use INFO, 4xx responses use WARNING, and 5xx responses use ERROR. Requests exceeding `SLOW_REQUEST_THRESHOLD_MS` produce an additional WARNING record with the same fields and request ID. The default threshold is 1000 ms.

## Identity and network behavior

Identity is obtained only by signature-validating the bearer JWT and reading its existing claims. Request logging never queries the database and never changes authentication results. Invalid or expired tokens simply produce `null` identity fields.

In the production Nginx topology, `X-Real-IP` is validated as an IPv4 or IPv6 address before logging. Otherwise, the direct ASGI peer address is used. The backend is not exposed directly by production Compose, so Nginx remains the trusted proxy boundary.

## Data safety

Request logs never include headers, bearer tokens, cookies, request or response bodies, query strings, passwords, password hashes, database URLs, API keys, prompts, or AI responses. Unexpected exceptions record only their exception type in the internal error log; the request record contains metadata only.

## Future integrations

Container stdout/stderr can be collected by Loki, ELK/OpenSearch, or a cloud logging agent. Each collector should parse the JSON message and index `request_id`, `status_code`, `duration_ms`, `path`, and user identity fields. Metrics and distributed tracing are intentionally not implemented in this phase; a future OpenTelemetry layer can reuse `request_id` as an application correlation field while adopting standard trace and span IDs.
