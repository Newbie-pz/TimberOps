"""Lightweight database and migration readiness diagnostics."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import NullPool

from app.db.connectivity import database_connect_args


logger = logging.getLogger("timberops.readiness")
BACKEND_ROOT = Path(__file__).resolve().parents[2]
READINESS_CONNECT_TIMEOUT_SECONDS = 2

DatabaseStatus = Literal["ok", "failed"]
MigrationStatus = Literal["ok", "outdated", "unknown"]


@dataclass(frozen=True)
class ReadinessResult:
    """Public-safe readiness categories with no infrastructure details."""

    database: DatabaseStatus
    migration: MigrationStatus

    @property
    def is_ready(self) -> bool:
        return self.database == "ok" and self.migration == "ok"

    def to_payload(self) -> dict[str, object]:
        return {
            "status": "ready" if self.is_ready else "not_ready",
            "checks": {
                "database": self.database,
                "migration": self.migration,
            },
        }


class ReadinessService:
    """Run read-only checks through the application's existing Engine."""

    def __init__(
        self,
        engine: Engine,
        *,
        expected_heads: tuple[str, ...] | None = None,
    ) -> None:
        self._engine = engine
        self._expected_heads = expected_heads

    def check(self) -> ReadinessResult:
        """Check connectivity and compare DB revisions without running migrations."""
        try:
            with readiness_connection(self._engine) as connection:
                connection.execute(text("SELECT 1"))
                try:
                    current_heads = tuple(
                        MigrationContext.configure(connection).get_current_heads()
                    )
                except Exception as exc:
                    _log_failure("migration revision read", exc)
                    return ReadinessResult(database="ok", migration="unknown")
        except Exception as exc:
            _log_failure("database", exc)
            return ReadinessResult(database="failed", migration="unknown")

        try:
            expected_heads = self._expected_heads or get_expected_migration_heads()
        except Exception as exc:
            _log_failure("expected migration revision", exc)
            return ReadinessResult(database="ok", migration="unknown")

        if not expected_heads:
            return ReadinessResult(database="ok", migration="unknown")
        if set(current_heads) == set(expected_heads):
            return ReadinessResult(database="ok", migration="ok")
        return ReadinessResult(database="ok", migration="outdated")


@contextmanager
def readiness_connection(engine: Engine) -> Generator[Connection, None, None]:
    """Open an isolated short-lived probe connection without a persistent pool."""
    if engine.url.get_backend_name() != "postgresql":
        with engine.connect() as connection:
            yield connection
        return

    probe_engine = create_engine(
        engine.url,
        poolclass=NullPool,
        hide_parameters=True,
        connect_args=database_connect_args(
            engine.url,
            connect_timeout_seconds=READINESS_CONNECT_TIMEOUT_SECONDS,
        ),
    )
    try:
        with probe_engine.connect() as connection:
            yield connection
    finally:
        probe_engine.dispose()


@lru_cache(maxsize=1)
def get_expected_migration_heads() -> tuple[str, ...]:
    """Load code heads once; this reads migration scripts but never executes them."""
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    return tuple(ScriptDirectory.from_config(config).get_heads())


def _log_failure(check: str, exc: Exception) -> None:
    """Record only an exception category, never connection or SQL details."""
    logger.warning(
        "readiness check failed check=%s error_type=%s",
        check,
        type(exc).__name__,
    )
