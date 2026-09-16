"""SQLAlchemy engine and request-scoped session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()
database_url = settings.require_database_url()


def _database_connect_args(url: str) -> dict[str, object]:
    """Bound PostgreSQL connection waits and match local Docker's IPv4 binding."""
    parsed_url = make_url(url)
    if parsed_url.get_backend_name() != "postgresql":
        return {}

    connect_args: dict[str, object] = {"connect_timeout": 10}
    if parsed_url.host and parsed_url.host.lower() == "localhost":
        # docker-compose publishes PostgreSQL on 127.0.0.1 only. Supplying
        # hostaddr prevents psycopg from waiting on an unreachable ::1 first.
        connect_args["hostaddr"] = "127.0.0.1"
    return connect_args

engine: Engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args=_database_connect_args(database_url),
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Yield one SQLAlchemy session and always close it after the request."""
    with SessionLocal() as session:
        yield session
