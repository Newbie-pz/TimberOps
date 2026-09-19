"""SQLAlchemy engine and request-scoped session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.connectivity import database_connect_args
from app.observability.metrics import register_db_pool_metrics


settings = get_settings()
database_url = settings.require_database_url()


engine: Engine = create_engine(
    database_url,
    pool_pre_ping=True,
    hide_parameters=not settings.debug,
    connect_args=database_connect_args(
        database_url,
        connect_timeout_seconds=10,
    ),
)
register_db_pool_metrics(engine)

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
