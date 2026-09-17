#!/bin/sh
set -eu

# A single backend container owns production migrations. A failed migration
# deliberately prevents the application server from starting.
alembic upgrade head

exec "$@"
