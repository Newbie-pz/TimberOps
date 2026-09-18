"""Prometheus-compatible application metrics with bounded, non-PII labels."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from decimal import Decimal
from threading import Lock
from typing import Protocol

from prometheus_client import (
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)
from sqlalchemy import event
from sqlalchemy.engine import Engine


logger = logging.getLogger("timberops.metrics")

# TimberOps owns an isolated registry so the endpoint exports only explicitly
# approved metrics, not process/environment collectors added by third parties.
METRICS_REGISTRY = CollectorRegistry(auto_describe=True)

HTTP_REQUESTS_TOTAL = Counter(
    "timberops_http_requests_total",
    "Number of completed TimberOps HTTP requests.",
    ("method", "path", "status_code"),
    registry=METRICS_REGISTRY,
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "timberops_http_request_duration_seconds",
    "TimberOps HTTP request duration in seconds.",
    ("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    registry=METRICS_REGISTRY,
)
AI_REQUESTS_TOTAL = Counter(
    "timberops_ai_requests_total",
    "Number of AI HTTP requests by provider and outcome class.",
    ("provider", "status"),
    registry=METRICS_REGISTRY,
)
AI_LATENCY_SECONDS = Histogram(
    "timberops_ai_latency_seconds",
    "AI HTTP request duration in seconds.",
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30, 60),
    registry=METRICS_REGISTRY,
)
BILLING_RECORDS_TOTAL = Counter(
    "timberops_billing_records_total",
    "Number of billing records entering each payment status.",
    ("status",),
    registry=METRICS_REGISTRY,
)
BILLING_AMOUNT_TOTAL = Histogram(
    "timberops_billing_amount_total",
    "Distribution of newly created billing record amounts in CNY.",
    buckets=(10, 30, 50, 100, 200, 500, 1000, 5000, 10000),
    registry=METRICS_REGISTRY,
)
WEIGHING_COMPLETED_TOTAL = Counter(
    "timberops_weighing_completed_total",
    "Number of weighing tasks successfully committed as completed.",
    registry=METRICS_REGISTRY,
)
DB_POOL_CHECKED_OUT = Gauge(
    "timberops_db_pool_checked_out",
    "Current SQLAlchemy connections checked out by application workers.",
    multiprocess_mode="livesum",
    registry=METRICS_REGISTRY,
)
DB_POOL_SIZE = Gauge(
    "timberops_db_pool_size",
    "Configured SQLAlchemy connection pool size across application workers.",
    multiprocess_mode="livesum",
    registry=METRICS_REGISTRY,
)


class _Pool(Protocol):
    checkedout: object
    size: object


_registered_pool_ids: set[int] = set()
_registered_pools: list[_Pool] = []
_registration_lock = Lock()


def observe_http_request(
    *, method: str, path: str, status_code: int, duration_seconds: float
) -> None:
    """Record one completed HTTP request using only bounded route metadata."""
    _safe_metric_update(
        lambda: HTTP_REQUESTS_TOTAL.labels(
            method=method,
            path=path,
            status_code=str(status_code),
        ).inc()
    )
    _safe_metric_update(
        lambda: HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method,
            path=path,
        ).observe(max(duration_seconds, 0.0))
    )


def observe_ai_request(
    *, provider: str, status: str, duration_seconds: float
) -> None:
    """Record AI lifecycle metadata without message or model payloads."""
    _safe_metric_update(
        lambda: AI_REQUESTS_TOTAL.labels(provider=provider, status=status).inc()
    )
    _safe_metric_update(
        lambda: AI_LATENCY_SECONDS.observe(max(duration_seconds, 0.0))
    )


def record_billing_created(*, status: str, amount: Decimal) -> None:
    """Count a newly committed fee snapshot and observe its amount once."""
    _safe_metric_update(lambda: BILLING_RECORDS_TOTAL.labels(status=status).inc())
    _safe_metric_update(lambda: BILLING_AMOUNT_TOTAL.observe(float(amount)))


def record_billing_status_transition(*, status: str) -> None:
    """Count one committed billing lifecycle transition."""
    _safe_metric_update(lambda: BILLING_RECORDS_TOTAL.labels(status=status).inc())


def record_weighing_completed() -> None:
    """Count one successfully committed task completion."""
    _safe_metric_update(WEIGHING_COMPLETED_TOTAL.inc)


def register_db_pool_metrics(engine: Engine) -> None:
    """Observe an engine pool without changing its connection configuration."""
    pool = engine.pool
    pool_id = id(pool)
    with _registration_lock:
        if pool_id in _registered_pool_ids:
            return
        _registered_pool_ids.add(pool_id)
        _registered_pools.append(pool)  # type: ignore[arg-type]

    @event.listens_for(pool, "checkout")
    def _on_checkout(*_: object) -> None:
        _refresh_pool(pool)  # type: ignore[arg-type]

    @event.listens_for(pool, "checkin")
    def _on_checkin(*_: object) -> None:
        _refresh_pool(pool)  # type: ignore[arg-type]

    _refresh_pool(pool)  # type: ignore[arg-type]


def render_metrics() -> tuple[bytes, str]:
    """Return current metrics, using Prometheus multiprocess aggregation when set."""
    for pool in tuple(_registered_pools):
        _refresh_pool(pool)

    if os.getenv("PROMETHEUS_MULTIPROC_DIR"):
        scrape_registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(scrape_registry)
    else:
        scrape_registry = METRICS_REGISTRY
    return generate_latest(scrape_registry), CONTENT_TYPE_LATEST


def _refresh_pool(pool: _Pool) -> None:
    """Best-effort pool sampling; unsupported pools report zero, never fail work."""
    try:
        checked_out_value = getattr(pool, "checkedout")
        checked_out = float(
            checked_out_value() if callable(checked_out_value) else checked_out_value
        )
    except (AttributeError, NotImplementedError, TypeError, ValueError):
        checked_out = 0.0
    try:
        size_value = getattr(pool, "size")
        size = float(size_value() if callable(size_value) else size_value)
    except (AttributeError, NotImplementedError, TypeError, ValueError):
        size = 0.0
    _safe_metric_update(lambda: DB_POOL_CHECKED_OUT.set(checked_out))
    _safe_metric_update(lambda: DB_POOL_SIZE.set(size))


def _safe_metric_update(update: Callable[[], None]) -> None:
    """Keep monitoring failures from changing completed business operations."""
    try:
        update()
    except Exception:  # pragma: no cover - defensive boundary around telemetry
        logger.exception("metric update failed")
