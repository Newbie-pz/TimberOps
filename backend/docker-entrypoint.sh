#!/bin/sh
set -eu

# A single backend container owns production migrations. A failed migration
# deliberately prevents the application server from starting.
alembic upgrade head

# Uvicorn runs multiple workers in production. Prometheus' multiprocess files
# must start empty for each fresh container lifecycle to avoid stale counters.
if [ "${PROMETHEUS_MULTIPROC_DIR:-}" = "/tmp/timberops-prometheus" ]; then
    mkdir -p /tmp/timberops-prometheus
    find /tmp/timberops-prometheus -type f -name '*.db' -delete
elif [ -n "${PROMETHEUS_MULTIPROC_DIR:-}" ]; then
    echo "Unsupported PROMETHEUS_MULTIPROC_DIR" >&2
    exit 1
fi

exec "$@"
