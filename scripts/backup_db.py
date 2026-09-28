"""Create a verified TimberOps PostgreSQL custom-format backup."""

from __future__ import annotations

import argparse
from pathlib import Path

from db_recovery import (
    DEFAULT_COMPOSE_FILE,
    ROOT,
    DockerDatabaseTarget,
    RecoveryError,
    create_backup,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=ROOT / "backups",
        help="archive directory (default: repository backups directory)",
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
        result = create_backup(target, output_directory=args.output_directory)
    except RecoveryError as exc:
        print(f"Backup failed: {exc}")
        return 1
    print(f"Backup completed: {result.path}")
    print(f"Archive size: {result.size_bytes} bytes")
    print(f"Integrity manifest: {result.manifest_path}")
    print(f"Alembic revision: {', '.join(result.inspection.revisions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
