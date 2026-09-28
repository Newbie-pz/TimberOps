"""Safely restore a TimberOps PostgreSQL backup into a new database."""

from __future__ import annotations

import argparse
from pathlib import Path

from db_recovery import (
    DEFAULT_COMPOSE_FILE,
    DockerDatabaseTarget,
    RecoveryError,
    restore_backup,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup_file", type=Path, help="custom-format .dump archive")
    parser.add_argument(
        "--target-database",
        required=True,
        help="new database name; an existing database is always refused",
    )
    parser.add_argument(
        "--confirm-restore",
        action="store_true",
        help="explicitly acknowledge creation and restoration of the target database",
    )
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--service", default="db")
    parser.add_argument(
        "--container",
        help="use a named PostgreSQL container instead of Docker Compose",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    target = DockerDatabaseTarget(
        compose_file=args.compose_file,
        service=args.service,
        container=args.container,
    )
    try:
        result = restore_backup(
            target,
            backup_path=args.backup_file,
            target_database=args.target_database,
            confirm_restore=args.confirm_restore,
        )
    except RecoveryError as exc:
        print(f"Restore failed: {exc}")
        return 1
    print(f"Restore completed into new database: {result.database_name}")
    print(f"Alembic revision: {', '.join(result.inspection.revisions)}")
    for table, count in sorted(result.inspection.table_counts.items()):
        print(f"Verified rows: {table}={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
