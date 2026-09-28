"""Unit tests for the manual PostgreSQL backup and restore tooling."""

from __future__ import annotations

import importlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPTS_DIRECTORY = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIRECTORY))
db_recovery = importlib.import_module("db_recovery")


def test_backup_filename_uses_utc_timestamp() -> None:
    value = db_recovery.backup_filename(
        datetime(2026, 9, 28, 9, 8, 7, tzinfo=timezone.utc)
    )

    assert value == "timberops_20260928T090807Z.dump"


def test_restore_requires_explicit_confirmation_before_any_io(tmp_path: Path) -> None:
    with pytest.raises(db_recovery.RecoveryError, match="--confirm-restore"):
        db_recovery.restore_backup(
            db_recovery.DockerDatabaseTarget(container="must-not-run"),
            backup_path=tmp_path / "missing.dump",
            target_database="timberops_restore",
            confirm_restore=False,
        )


def test_restore_rejects_invalid_or_empty_backup_path(tmp_path: Path) -> None:
    target = db_recovery.DockerDatabaseTarget(container="must-not-run")
    with pytest.raises(db_recovery.RecoveryError, match="does not exist"):
        db_recovery.restore_backup(
            target,
            backup_path=tmp_path / "missing.dump",
            target_database="timberops_restore",
            confirm_restore=True,
        )

    empty_backup = tmp_path / "empty.dump"
    empty_backup.touch()
    with pytest.raises(db_recovery.RecoveryError, match="empty"):
        db_recovery.restore_backup(
            target,
            backup_path=empty_backup,
            target_database="timberops_restore",
            confirm_restore=True,
        )


def test_database_utility_failure_is_propagated_without_stderr_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=["docker"],
            returncode=2,
            stdout=b"",
            stderr=b"password=never-print DATABASE_URL=postgresql://private",
        )

    monkeypatch.setattr(db_recovery.subprocess, "run", failed_run)
    target = db_recovery.DockerDatabaseTarget(container="test-db")

    with pytest.raises(db_recovery.RecoveryError) as error:
        target.environment_value("POSTGRES_DB")

    message = str(error.value)
    assert "exit code 2" in message
    assert "never-print" not in message
    assert "postgresql://" not in message


def test_empty_pg_dump_output_is_not_a_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = db_recovery.DockerDatabaseTarget(container="test-db")
    monkeypatch.setattr(
        target.__class__,
        "environment_value",
        lambda self, name: "timberops" if name == "POSTGRES_DB" else "operator",
    )
    monkeypatch.setattr(
        db_recovery,
        "inspect_database",
        lambda *args, **kwargs: db_recovery.DatabaseInspection(
            revisions=("revision",),
            table_counts={table: 0 for table in db_recovery.CORE_TABLES},
        ),
    )
    monkeypatch.setattr(
        target.__class__,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args=["pg_dump"], returncode=0, stdout=b"", stderr=b""
        ),
    )

    with pytest.raises(db_recovery.RecoveryError, match="empty archive"):
        db_recovery.create_backup(target, output_directory=tmp_path)

    assert not list(tmp_path.iterdir())


class _RestoreTarget:
    def __init__(self, *, existing_target: bool = False) -> None:
        self.existing_target = existing_target
        self.commands: list[list[str]] = []

    def environment_value(self, name: str) -> str:
        return "timberops_source" if name == "POSTGRES_DB" else "timberops"

    def run(self, command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        self.commands.append(command)
        output = b""
        if command[0] == "psql":
            sql = command[-1]
            if "FROM pg_database" in sql:
                databases = ["postgres", "timberops_source"]
                if self.existing_target:
                    databases.append("timberops_restore")
                output = ("\n".join(databases) + "\n").encode()
            elif "FROM alembic_version" in sql:
                output = b"revision_1\n"
            elif "information_schema.tables" in sql:
                output = ("\n".join(db_recovery.CORE_TABLES) + "\n").encode()
            elif "COUNT(*)" in sql:
                output = "".join(
                    f"{table}|1\n" for table in db_recovery.CORE_TABLES
                ).encode()
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr=b"")


def test_restore_creates_only_a_new_database_via_maintenance_database(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "valid.dump"
    archive.write_bytes(b"custom-format-placeholder")
    target = _RestoreTarget()

    result = db_recovery.restore_backup(
        target,
        backup_path=archive,
        target_database="timberops_restore",
        confirm_restore=True,
    )

    createdb = next(command for command in target.commands if command[0] == "createdb")
    assert createdb[-1] == "timberops_restore"
    assert createdb[createdb.index("--maintenance-db") + 1] == "timberops_source"
    assert result.inspection.revisions == ("revision_1",)
    assert result.inspection.table_counts["weighing_tasks"] == 1


def test_restore_refuses_an_existing_target_database(tmp_path: Path) -> None:
    archive = tmp_path / "valid.dump"
    archive.write_bytes(b"custom-format-placeholder")
    target = _RestoreTarget(existing_target=True)

    with pytest.raises(db_recovery.RecoveryError, match="already exists"):
        db_recovery.restore_backup(
            target,
            backup_path=archive,
            target_database="timberops_restore",
            confirm_restore=True,
        )

    assert not any(command[0] == "createdb" for command in target.commands)
