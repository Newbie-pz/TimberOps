"""Permission enforcement on the first protected API surface."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.integrations.ai.agent.graph import AgentResult
from app.integrations.ai.dependencies import get_ai_agent
from app.main import app
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.security.jwt import create_access_token


def _headers_for_role(engine: Engine, role_name: str, username: str) -> dict[str, str]:
    with Session(engine) as session:
        role = session.scalar(select(Role).where(Role.name == role_name))
        assert role is not None
        user = User(username=username, password_hash="not-used", real_name=username)
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()
        token = create_access_token(user_id=user.id, username=user.username)
    return {"Authorization": f"Bearer {token}"}


def _headers_without_role(engine: Engine, username: str) -> dict[str, str]:
    with Session(engine) as session:
        user = User(username=username, password_hash="not-used", real_name=username)
        session.add(user)
        session.commit()
        token = create_access_token(user_id=user.id, username=user.username)
    return {"Authorization": f"Bearer {token}"}


def _create_vehicle(client: TestClient, plate: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/vehicles",
        json={
            "plate_number": plate,
            "vehicle_type": "LARGE",
            "allowed_gross_weight_tons": "49.000",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_vehicle_delete_requires_authentication_and_permission(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    vehicle = _create_vehicle(api_client, "蒙H88001")
    operator_headers = _headers_for_role(
        db_engine,
        "OPERATOR",
        "delete_operator",
    )

    no_token = api_client.request(
        "DELETE",
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"reason": "测试"},
        headers={"Authorization": ""},
    )
    denied = api_client.request(
        "DELETE",
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"reason": "测试"},
        headers=operator_headers,
    )
    allowed = api_client.request(
        "DELETE",
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"reason": "测试"},
    )

    assert no_token.status_code == 401
    assert denied.status_code == 403
    assert denied.json() == {
        "error": {"code": "PERMISSION_DENIED", "message": "Permission denied"}
    }
    assert allowed.status_code == 204


def test_operator_can_create_and_complete_weighing_but_viewer_cannot(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    vehicle = _create_vehicle(api_client, "蒙H88002")
    operator_headers = _headers_for_role(
        db_engine,
        "OPERATOR",
        "weighing_operator",
    )
    viewer_headers = _headers_for_role(db_engine, "VIEWER", "weighing_viewer")

    denied_create = api_client.post(
        "/api/v1/weighing/tasks",
        json={"vehicle_id": vehicle["id"], "cargo_type": "COAL"},
        headers=viewer_headers,
    )
    created = api_client.post(
        "/api/v1/weighing/tasks",
        json={"vehicle_id": vehicle["id"], "cargo_type": "COAL"},
        headers=operator_headers,
    )
    assert denied_create.status_code == 403
    assert created.status_code == 201
    task_id = created.json()["id"]

    assert api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/tare",
        json={"weight_tons": "15.000"},
        headers=operator_headers,
    ).status_code == 200
    assert api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/wait-gross",
        headers=operator_headers,
    ).status_code == 200
    assert api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/gross",
        json={"weight_tons": "45.000"},
        headers=operator_headers,
    ).status_code == 200

    denied_complete = api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/complete",
        headers=viewer_headers,
    )
    allowed_complete = api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/complete",
        headers=operator_headers,
    )

    assert denied_complete.status_code == 403
    assert allowed_complete.status_code == 200


class _StubAgent:
    async def achat(self, message: str) -> AgentResult:
        del message
        return AgentResult(answer="允许查询", tool_calls=[])


def test_ai_query_and_export_permissions(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    viewer_headers = _headers_for_role(db_engine, "VIEWER", "query_viewer")
    no_role_headers = _headers_without_role(db_engine, "query_no_role")
    app.dependency_overrides[get_ai_agent] = lambda: _StubAgent()
    try:
        ai_denied = api_client.post(
            "/api/v1/ai/chat",
            json={"message": "今日称重"},
            headers=no_role_headers,
        )
        ai_allowed = api_client.post(
            "/api/v1/ai/chat",
            json={"message": "今日称重"},
            headers=viewer_headers,
        )
    finally:
        app.dependency_overrides.pop(get_ai_agent, None)

    export_denied = api_client.get(
        "/api/v1/export/weighing",
        headers=no_role_headers,
    )
    export_allowed = api_client.get(
        "/api/v1/export/weighing",
        headers=viewer_headers,
    )

    assert ai_denied.status_code == 403
    assert ai_allowed.status_code == 200
    assert export_denied.status_code == 403
    assert export_allowed.status_code == 200


def test_admin_can_assign_role_and_user_can_read_grants(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        viewer = session.scalar(select(Role).where(Role.name == "VIEWER"))
        user = User(username="role_target", password_hash="hash", real_name="目标用户")
        session.add(user)
        session.commit()
        assert viewer is not None
        user_id = user.id
        viewer_id = viewer.id
        token = create_access_token(user_id=user.id, username=user.username)

    operator_headers = _headers_for_role(
        db_engine,
        "OPERATOR",
        "role_assignment_operator",
    )

    denied = api_client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_id": str(viewer_id)},
        headers=operator_headers,
    )

    assigned = api_client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_id": str(viewer_id)},
    )
    roles = api_client.get(
        "/api/v1/auth/roles",
        headers={"Authorization": f"Bearer {token}"},
    )
    permissions = api_client.get(
        "/api/v1/auth/permissions",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert denied.status_code == 403
    assert assigned.status_code == 201
    assert [role["name"] for role in roles.json()] == ["VIEWER"]
    assert {item["code"] for item in permissions.json()} == {
        "vehicle:view",
        "customer:view",
        "weighing:view",
        "billing:view",
        "export:data",
        "ai:query",
    }

    removed = api_client.delete(
        f"/api/v1/users/{user_id}/roles/{viewer_id}"
    )
    roles_after_removal = api_client.get(
        "/api/v1/auth/roles",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert removed.status_code == 204
    assert roles_after_removal.json() == []
