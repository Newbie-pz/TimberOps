"""Shared isolated SQLAlchemy test database."""

import os
from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Keep test collection independent from a developer's ignored .env file.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-jwt-secret-key-32-characters-minimum",
)

import app.models  # noqa: F401  # Register all mapped tables.
from app.db.session import get_db
from app.db.base import Base
from app.domain.enums import VehicleType
from app.main import app
from app.models.billing import BillingRule


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    """Create a fresh shared in-memory engine for one test."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    seed_session = sessionmaker(bind=engine, expire_on_commit=False)
    with seed_session() as session:
        effective_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
        session.add_all(
            [
                BillingRule(
                    vehicle_type=VehicleType.SMALL,
                    fee_amount=Decimal("10.00"),
                    currency="CNY",
                    effective_time=effective_time,
                ),
                BillingRule(
                    vehicle_type=VehicleType.MEDIUM,
                    fee_amount=Decimal("30.00"),
                    currency="CNY",
                    effective_time=effective_time,
                ),
                BillingRule(
                    vehicle_type=VehicleType.LARGE,
                    fee_amount=Decimal("100.00"),
                    currency="CNY",
                    effective_time=effective_time,
                ),
            ]
        )
        session.commit()
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Generator[Session, None, None]:
    """Provide a fresh in-memory database for each service test."""
    testing_session = sessionmaker(bind=db_engine, expire_on_commit=False)
    with testing_session() as session:
        yield session


@pytest.fixture
def api_client(db_engine: Engine) -> Generator[TestClient, None, None]:
    """Provide an API client whose Depends(get_db) uses the test database."""
    testing_session = sessionmaker(bind=db_engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)
