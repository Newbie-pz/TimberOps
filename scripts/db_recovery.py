"""Shared PostgreSQL backup and restore primitives for TimberOps.

The module intentionally delegates database archive handling to the PostgreSQL
client tools inside an existing Docker container. It never reads or prints a
database password or a SQLAlchemy database URL.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPOSE_FILE = ROOT / "docker-compose.prod.yml"
CORE_TABLES = (
    "users",
    "vehicles",
    "customers",
    "weighing_tasks",
    "weighing_records",
    "billing_records",
    "audit_logs",
)
DATABASE_NAME_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,62}\Z")


class RecoveryError(RuntimeError):
    """A safe, user-facing backup or restore failure."""


@dataclass(frozen=True)
class DatabaseInspection:
    """Non-sensitive schema and row-count details used for restore validation."""

    revisions: tuple[str, ...]
    table_counts: dict[str, int]


@dataclass(frozen=True)
class BackupResult:
    path: Path
    manifest_path: Path
    size_bytes: int
    inspection: DatabaseInspection


@dataclass(frozen=True)
class RestoreResult:
    database_name: str
    inspection: DatabaseInspection


@dataclass(frozen=True)
class DockerDatabaseTarget:
    """PostgreSQL client execution target: Compose service or named container."""

    compose_file: Path = DEFAULT_COMPOSE_FILE
    service: str = "db"
    container: str | None = None

    def _prefix(self) -> list[str]:
        if self.container:
            return ["docker", "exec", "-i", self.container]
        return [
            "docker",
            "compose",
            "-f",
            str(self.compose_file),
            "exec",
            "-T",
            self.service,
        ]

    def run(
        self,
        command: Sequence[str],
        *,
        step: str,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | int = subprocess.PIPE,
    ) -> subprocess.CompletedProcess[bytes]:
        """Run a fixed database utility command and redact its failure output."""
        try:
            result = subprocess.run(
                [*self._prefix(), *command],
                cwd=ROOT,
                stdin=stdin,
                stdout=stdout,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError as exc:
            raise RecoveryError(f"{step} could not start Docker") from exc
        if result.returncode != 0:
            raise RecoveryError(
                f"{step} failed with exit code {result.returncode}; "
                "database utility output was withheld to avoid leaking configuration"
            )
        return result

    def environment_value(self, name: str) -> str:
        if name not in {"POSTGRES_DB", "POSTGRES_USER"}:
            raise RecoveryError("attempted to read a disallowed container variable")
        result = self.run(["printenv", name], step=f"read {name}")
        value = result.stdout.decode("utf-8", errors="strict").strip()
        if not value:
            raise RecoveryError(f"{name} is not configured in the database container")
        return value


def backup_filename(now: datetime | None = None) -> str:
    """Return a deterministic UTC archive name without host-specific characters."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    timestamp = current.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"timberops_{timestamp}.dump"


def _validate_database_name(value: str) -> str:
    if not DATABASE_NAME_PATTERN.fullmatch(value):
        raise RecoveryError(
            "database name must start with a letter or underscore and contain only "
            "letters, digits, or underscores"
        )
    return value


def _query(
    target: DockerDatabaseTarget,
    *,
    username: str,
    database_name: str,
    sql: str,
    step: str,
) -> list[str]:
    result = target.run(
        [
            "psql",
            "--no-psqlrc",
            "--no-password",
            "--set",
            "ON_ERROR_STOP=1",
            "--tuples-only",
            "--no-align",
            "--username",
            username,
            "--dbname",
            database_name,
            "--command",
            sql,
        ],
        step=step,
    )
    return [line.strip() for line in result.stdout.decode("utf-8").splitlines() if line.strip()]


def inspect_database(
    target: DockerDatabaseTarget,
    *,
    username: str,
    database_name: str,
) -> DatabaseInspection:
    """Verify migration metadata and required tables, then return row counts."""
    revisions = tuple(
        _query(
            target,
            username=username,
            database_name=database_name,
            sql="SELECT version_num FROM alembic_version ORDER BY version_num",
            step="read Alembic revision",
        )
    )
    if not revisions:
        raise RecoveryError("database does not contain an Alembic revision")

    quoted_tables = ", ".join(f"'{table}'" for table in CORE_TABLES)
    present_tables = set(
        _query(
            target,
            username=username,
            database_name=database_name,
            sql=(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                f"AND table_name IN ({quoted_tables}) ORDER BY table_name"
            ),
            step="verify required tables",
        )
    )
    missing_tables = sorted(set(CORE_TABLES) - present_tables)
    if missing_tables:
        raise RecoveryError(
            "database is missing required tables: " + ", ".join(missing_tables)
        )

    count_sql = " UNION ALL ".join(
        f"SELECT '{table}|' || COUNT(*) FROM {table}" for table in CORE_TABLES
    )
    count_lines = _query(
        target,
        username=username,
        database_name=database_name,
        sql=count_sql,
        step="count required table rows",
    )
    counts: dict[str, int] = {}
    for line in count_lines:
        table, count = line.split("|", maxsplit=1)
        counts[table] = int(count)
    if set(counts) != set(CORE_TABLES):
        raise RecoveryError("database row-count verification was incomplete")
    return DatabaseInspection(revisions=revisions, table_counts=counts)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_backup(
    target: DockerDatabaseTarget,
    *,
    output_directory: Path,
    filename: str | None = None,
) -> BackupResult:
    """Create a custom-format archive and a non-secret integrity manifest."""
    username = target.environment_value("POSTGRES_USER")
    database_name = target.environment_value("POSTGRES_DB")
    inspection = inspect_database(
        target,
        username=username,
        database_name=database_name,
    )

    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / (filename or backup_filename())
    if output_path.exists():
        raise RecoveryError(f"backup destination already exists: {output_path}")
    partial_path = output_path.with_suffix(output_path.suffix + ".part")
    partial_path.unlink(missing_ok=True)

    try:
        with partial_path.open("wb") as destination:
            target.run(
                [
                    "pg_dump",
                    "--no-password",
                    "--format=custom",
                    "--no-owner",
                    "--no-privileges",
                    "--username",
                    username,
                    "--dbname",
                    database_name,
                ],
                step="PostgreSQL backup",
                stdout=destination,
            )
        size_bytes = partial_path.stat().st_size
        if size_bytes <= 0:
            raise RecoveryError("PostgreSQL backup produced an empty archive")
        partial_path.replace(output_path)
    except Exception:
        partial_path.unlink(missing_ok=True)
        raise

    try:
        output_path.chmod(0o600)
    except OSError:
        pass

    manifest_path = output_path.with_suffix(output_path.suffix + ".json")
    manifest = {
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database_name": database_name,
        "alembic_revisions": list(inspection.revisions),
        "archive_filename": output_path.name,
        "archive_size_bytes": size_bytes,
        "archive_sha256": _sha256(output_path),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return BackupResult(
        path=output_path,
        manifest_path=manifest_path,
        size_bytes=size_bytes,
        inspection=inspection,
    )


def _load_manifest(backup_path: Path) -> dict[str, object] | None:
    manifest_path = backup_path.with_suffix(backup_path.suffix + ".json")
    if not manifest_path.exists():
        return None
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError("backup manifest is unreadable or invalid") from exc
    if not isinstance(value, dict):
        raise RecoveryError("backup manifest must contain a JSON object")
    return value


def restore_backup(
    target: DockerDatabaseTarget,
    *,
    backup_path: Path,
    target_database: str,
    confirm_restore: bool,
) -> RestoreResult:
    """Restore into a new database; existing databases are never overwritten."""
    if not confirm_restore:
        raise RecoveryError("restore refused: pass --confirm-restore to acknowledge the operation")
    if not backup_path.is_file():
        raise RecoveryError(f"backup file does not exist: {backup_path}")
    if backup_path.stat().st_size <= 0:
        raise RecoveryError("backup file is empty")
    target_database = _validate_database_name(target_database)

    manifest = _load_manifest(backup_path)
    if manifest is not None:
        expected_size = manifest.get("archive_size_bytes")
        expected_hash = manifest.get("archive_sha256")
        if expected_size != backup_path.stat().st_size or expected_hash != _sha256(backup_path):
            raise RecoveryError("backup archive does not match its integrity manifest")

    username = target.environment_value("POSTGRES_USER")
    source_database = target.environment_value("POSTGRES_DB")
    if target_database == source_database:
        raise RecoveryError("restore target must differ from the container's configured database")

    with backup_path.open("rb") as archive:
        target.run(
            ["pg_restore", "--list"],
            step="validate PostgreSQL archive",
            stdin=archive,
        )

    existing = _query(
        target,
        username=username,
        database_name=source_database,
        sql="SELECT datname FROM pg_database ORDER BY datname",
        step="check restore target",
    )
    if target_database in existing:
        raise RecoveryError(
            f"restore target database already exists: {target_database}; "
            "choose a new empty database name"
        )

    target.run(
        [
            "createdb",
            "--no-password",
            "--username",
            username,
            "--maintenance-db",
            source_database,
            "--encoding=UTF8",
            target_database,
        ],
        step="create restore target database",
    )
    try:
        with backup_path.open("rb") as archive:
            target.run(
                [
                    "pg_restore",
                    "--no-password",
                    "--exit-on-error",
                    "--no-owner",
                    "--no-privileges",
                    "--username",
                    username,
                    "--dbname",
                    target_database,
                ],
                step="restore PostgreSQL archive",
                stdin=archive,
            )
        inspection = inspect_database(
            target,
            username=username,
            database_name=target_database,
        )
    except Exception as exc:
        raise RecoveryError(
            "restore validation failed; the newly created target database was retained "
            "for inspection and the configured source database was not modified"
        ) from exc

    if manifest is not None:
        expected_revisions = manifest.get("alembic_revisions")
        if expected_revisions != list(inspection.revisions):
            raise RecoveryError(
                "restored Alembic revision does not match the backup manifest; "
                "the source database was not modified"
            )
    return RestoreResult(database_name=target_database, inspection=inspection)
