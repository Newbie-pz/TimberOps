# Weighbridge integration

TimberOps exposes a vendor-neutral, read-only weighbridge boundary while preserving the existing manual weighing workflow. A device read is only a transient candidate value. It never creates a `WeighingRecord`, changes a task, advances the state machine, or triggers Billing.

## Current modes

`WEIGHBRIDGE_MODE=manual` is the default. Operators enter tare, gross, and reweigh values exactly as before. The status endpoint reports manual mode and the weight endpoint returns `WEIGHBRIDGE_MANUAL_MODE`. This is also the operational fallback when device acquisition is unavailable.

`WEIGHBRIDGE_MODE=simulator` enables the deterministic development adapter. It accepts a comma-separated sequence such as:

```dotenv
WEIGHBRIDGE_MODE=simulator
WEIGHBRIDGE_SIMULATOR_WEIGHTS=48.120,48.125,48.123
WEIGHBRIDGE_SIMULATOR_STABLE=true
WEIGHBRIDGE_SIMULATOR_STATUS=online
```

Values are returned in order and the last value is repeated. No random data is used. `WEIGHBRIDGE_SIMULATOR_STATUS` also supports `offline`, `timeout`, and `error`; these modes fail immediately and do not block a FastAPI worker.

Only `manual` and `simulator` are accepted configuration values. Serial and TCP are intentionally not advertised as implemented.

## Adapter boundary

`WeighbridgeAdapter` has two operations:

- `get_status()` reports the bounded device state and whether reads are available.
- `read_weight()` returns a positive finite `Decimal` weight in tonnes, a stability flag, a UTC timestamp, and device status, or raises a typed integration error.

The process constructs one adapter instance at startup. The simulator protects its deterministic sequence with a lock. Future adapters can maintain connection state behind the same interface without changing weighing business services.

## HTTP API and RBAC

- `GET /api/v1/weighbridge/status`
- `GET /api/v1/weighbridge/weight`

Both endpoints require the existing `weighing:view` permission. They do not accept a task ID and cannot write business data. The frontend may copy a stable value into the current manual form, but the operator must still click the existing tare, gross, or reweigh submit action. Those actions retain their existing permissions, validation, state transitions, audit trail, and transactions.

Expected acquisition failures use the standard error envelope:

- manual mode: HTTP 409 / `WEIGHBRIDGE_MANUAL_MODE`
- offline: HTTP 503 / `WEIGHBRIDGE_OFFLINE`
- timeout: HTTP 504 / `WEIGHBRIDGE_TIMEOUT`
- read/protocol or invalid weight: HTTP 502 / `WEIGHBRIDGE_READ_ERROR` or `WEIGHBRIDGE_INVALID_WEIGHT`

Device availability is a degraded capability. It is intentionally excluded from `/health` and `/ready`, because history, billing, reports, audit, and manual weighing remain usable.

## Observability and safety

The adapter emits only mode, bounded outcome, and latency metadata. It does not log raw protocol frames, weights, task IDs, plates, customers, users, tokens, or request bodies.

Prometheus metrics are low-cardinality:

- `timberops_weighbridge_reads_total{adapter,status}`
- `timberops_weighbridge_device_online{adapter}`

The current weighing record source remains `MANUAL`, even when an operator copies a simulator value into the form. That is deliberate: there is no trusted end-to-end device provenance in this phase, and falsely marking a manually confirmed request as an automatic device record would weaken audit meaning. Adding reliable `DEVICE` provenance requires a future command contract and an explicit business decision.

## Real hardware integration prerequisites

Do not implement a Serial or TCP adapter until the selected scale vendor provides the protocol. A production integration requires:

1. Obtain the vendor protocol and example frames.
2. Confirm the physical interface (for example RS-232, RS-485, or TCP) and deployment topology.
3. Implement a new adapter with explicit connection and read timeouts.
4. Validate units, decimal precision, framing, checksums, and the vendor's stable flag or an approved sampling rule.
5. Test disconnect, reconnect, malformed frames, and device restart behavior.
6. Complete onsite calibration and UAT against certified scale readings.

Raw device frames should remain disabled in normal logs. If protocol diagnostics are later added, they must be explicitly gated, redacted, and time-bounded.
