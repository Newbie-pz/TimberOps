"""Database connection configuration tests."""

from app.db.connectivity import database_connect_args


def test_local_postgresql_uses_ipv4_hostaddr_and_bounded_connect_timeout() -> None:
    args = database_connect_args(
        "postgresql+psycopg://user:password@localhost:5432/timberops",
        connect_timeout_seconds=10,
    )

    assert args == {"connect_timeout": 10, "hostaddr": "127.0.0.1"}


def test_remote_postgresql_keeps_hostname_resolution() -> None:
    args = database_connect_args(
        "postgresql+psycopg://user:password@db.internal:5432/timberops",
        connect_timeout_seconds=10,
    )

    assert args == {"connect_timeout": 10}


def test_non_postgresql_database_receives_no_driver_specific_args() -> None:
    assert (
        database_connect_args(
            "sqlite+pysqlite:///:memory:",
            connect_timeout_seconds=10,
        )
        == {}
    )
