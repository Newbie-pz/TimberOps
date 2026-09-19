"""Shared PostgreSQL connection arguments for business and probe connections."""

from sqlalchemy.engine import URL, make_url


def database_connect_args(
    url: str | URL,
    *,
    connect_timeout_seconds: int,
) -> dict[str, object]:
    """Build bounded driver arguments while preserving localhost IPv4 routing."""
    parsed_url = make_url(url)
    if parsed_url.get_backend_name() != "postgresql":
        return {}

    connect_args: dict[str, object] = {
        "connect_timeout": connect_timeout_seconds,
    }
    if parsed_url.host and parsed_url.host.lower() == "localhost":
        # docker-compose publishes PostgreSQL on 127.0.0.1 only. Supplying
        # hostaddr prevents psycopg from waiting on an unreachable ::1 first.
        connect_args["hostaddr"] = "127.0.0.1"
    return connect_args
