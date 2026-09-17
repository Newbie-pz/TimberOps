"""Authentication, authorization, and payload contract for dashboard API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.models.rbac import Role, UserRole
from app.models.user import User
from app.security.jwt import create_access_token


def test_dashboard_overview_returns_empty_structured_payload(
    api_client: TestClient,
) -> None:
    response = api_client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["timezone"] == "UTC+08:00"
    assert body["currency"] == "CNY"
    assert body["today_task_count"] == 0
    assert body["today_completed_net_weight_tons"] == "0.000"
    assert body["today_income"] == "0.00"
    assert body["cargo_weight_ranking"] == []
    assert body["vehicle_transport_ranking"] == []
    assert len(body["status_distribution"]) == 6


def test_dashboard_requires_dashboard_view_permission(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        user = User(
            username="dashboard_denied",
            password_hash="not-used",
            real_name="无看板权限",
        )
        session.add(user)
        session.commit()
        token = create_access_token(user_id=user.id, username=user.username)

    response = api_client.get(
        "/api/v1/dashboard/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.parametrize("role_name", ["OPERATOR", "VIEWER"])
def test_dashboard_is_available_to_non_admin_builtin_roles(
    api_client: TestClient,
    db_engine: Engine,
    role_name: str,
) -> None:
    with Session(db_engine) as session:
        role = session.scalar(select(Role).where(Role.name == role_name))
        assert role is not None
        username = f"dashboard_{role_name.lower()}"
        user = User(username=username, password_hash="not-used", real_name=username)
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()
        token = create_access_token(user_id=user.id, username=user.username)

    response = api_client.get(
        "/api/v1/dashboard/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
