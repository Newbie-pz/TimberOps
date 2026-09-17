"""Shared isolated SQLAlchemy test database."""

import os
from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Keep test collection independent from a developer's ignored .env file.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "test-only-jwt-secret-key-32-characters-minimum",
)
os.environ.setdefault("PUBLIC_REGISTRATION_ENABLED", "true")

import app.models  # noqa: F401  # Register all mapped tables.
from app.db.session import get_db
from app.api.dependencies import get_security_session_factory
from app.db.base import Base
from app.domain.enums import VehicleType
from app.domain.rbac_catalog import (
    PERMISSION_DEFINITIONS,
    ROLE_DEFINITIONS,
    ROLE_PERMISSION_CODES,
)
from app.main import app
from app.models.billing import BillingRule
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User
from app.security.jwt import create_access_token


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
        roles = {
            name: Role(name=name, description=description)
            for name, description in ROLE_DEFINITIONS
        }
        permissions = {
            code: Permission(code=code, name=name, description=name)
            for code, name in PERMISSION_DEFINITIONS
        }
        session.add_all([*roles.values(), *permissions.values()])
        session.flush()
        session.add_all(
            [
                RolePermission(
                    role_id=roles[role_name].id,
                    permission_id=permissions[permission_code].id,
                )
                for role_name, permission_codes in ROLE_PERMISSION_CODES.items()
                for permission_code in permission_codes
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

    with testing_session() as session:
        admin_role = session.scalar(select(Role).where(Role.name == "ADMIN"))
        assert admin_role is not None
        admin_user = User(
            username="test_admin",
            password_hash="not-used-by-token-authentication",
            real_name="测试管理员",
        )
        session.add(admin_user)
        session.flush()
        session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
        session.commit()
        admin_token = create_access_token(
            user_id=admin_user.id,
            username=admin_user.username,
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_security_session_factory] = lambda: testing_session
    with TestClient(app) as client:
        client.headers.update({"Authorization": f"Bearer {admin_token}"})
        yield client
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_security_session_factory, None)
