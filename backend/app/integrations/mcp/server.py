"""Standalone stateless Streamable HTTP MCP server for TimberOps queries."""

from mcp.server import MCPServer
from starlette.applications import Starlette

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.integrations.mcp.tools import SessionFactory, register_analytics_tools


SERVER_NAME = "TimberOps Read-only Business Server"
SERVER_VERSION = "0.1.0"


def create_mcp_server(session_factory: SessionFactory = SessionLocal) -> MCPServer:
    """Create an isolated MCP server backed by request-scoped DB sessions."""
    server = MCPServer(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        description="Read-only vehicle weighing analytics for TimberOps.",
        instructions=(
            "All tools are read-only and return structured TimberOps business data. "
            "Weight values are decimal strings in metric tons."
        ),
    )
    register_analytics_tools(server, session_factory)
    return server


def create_streamable_http_app(server: MCPServer) -> Starlette:
    """Expose the server through stateless Streamable HTTP with JSON responses."""
    settings = get_settings()
    return server.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        host=settings.mcp_host,
    )


mcp_server = create_mcp_server()
app = create_streamable_http_app(mcp_server)


def main() -> None:
    """Run the standalone MCP process for local development."""
    settings = get_settings()
    mcp_server.run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )


if __name__ == "__main__":
    main()
