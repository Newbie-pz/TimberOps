"""Protocol-level tests for the read-only TimberOps MCP Server."""

import asyncio
from collections.abc import Coroutine
from typing import Any

from fastapi.testclient import TestClient
from mcp import Client
from mcp.server import MCPServer
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.integrations.mcp.server import (
    SERVER_NAME,
    create_mcp_server,
    create_streamable_http_app,
)


EXPECTED_TOOLS = {
    "get_today_weighing_summary",
    "get_cargo_weight_summary",
    "get_overweight_records",
    "get_vehicle_weighing_history",
    "get_weighing_task_detail",
}


def _server(db_engine: Engine) -> MCPServer:
    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    return create_mcp_server(session_factory)


def _run(coroutine: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coroutine)


def test_streamable_http_server_starts(db_engine: Engine) -> None:
    server = _server(db_engine)
    http_app = create_streamable_http_app(server)

    with TestClient(http_app):
        routes = {route.path for route in http_app.routes}

    assert routes == {"/mcp"}
    assert server.name == SERVER_NAME


def test_mcp_lists_exactly_five_read_only_tools(db_engine: Engine) -> None:
    server = _server(db_engine)

    async def scenario() -> Any:
        async with Client(server) as client:
            return await client.list_tools()

    result = _run(scenario())

    assert {tool.name for tool in result.tools} == EXPECTED_TOOLS
    for tool in result.tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.open_world_hint is False


def test_all_mcp_tools_publish_input_and_output_schemas(
    db_engine: Engine,
) -> None:
    server = _server(db_engine)

    async def scenario() -> Any:
        async with Client(server) as client:
            return await client.list_tools()

    tools = {tool.name: tool for tool in _run(scenario()).tools}

    assert set(tools) == EXPECTED_TOOLS
    for tool in tools.values():
        assert tool.input_schema["type"] == "object"
        assert tool.output_schema is not None
        assert tool.output_schema["type"] == "object"
    assert "cargo_type" in tools["get_cargo_weight_summary"].input_schema[
        "required"
    ]
    assert "plate_number" in tools["get_vehicle_weighing_history"].input_schema[
        "required"
    ]
    assert "task_no" in tools["get_weighing_task_detail"].input_schema["required"]


def test_mcp_tool_call_executes_analytics_service(db_engine: Engine) -> None:
    server = _server(db_engine)

    async def scenario() -> Any:
        async with Client(server) as client:
            return await client.call_tool("get_today_weighing_summary", {})

    result = _run(scenario())

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["completed_tasks"] == 0
    assert result.structured_content["total_net_weight_tons"] == "0.000"


def test_all_mcp_tools_return_structured_json(db_engine: Engine) -> None:
    server = _server(db_engine)
    calls = {
        "get_today_weighing_summary": {},
        "get_cargo_weight_summary": {"cargo_type": "COAL"},
        "get_overweight_records": {},
        "get_vehicle_weighing_history": {"plate_number": "蒙H00000"},
        "get_weighing_task_detail": {"task_no": "WT-NOT-FOUND"},
    }

    async def scenario() -> dict[str, Any]:
        async with Client(server) as client:
            return {
                name: await client.call_tool(name, arguments)
                for name, arguments in calls.items()
            }

    results = _run(scenario())

    assert set(results) == EXPECTED_TOOLS
    for result in results.values():
        assert result.is_error is False
        assert isinstance(result.structured_content, dict)
    assert results["get_overweight_records"].structured_content == {"records": []}
    assert results["get_vehicle_weighing_history"].structured_content == {
        "plate_number": "蒙H00000",
        "tasks": [],
    }
    assert results["get_weighing_task_detail"].structured_content["found"] is False
