"""Audit log API filtering, operator resolution, and permission matrix."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.security.jwt import create_access_token


def _headers_for_role(engine: Engine, role_name: str) -> dict[str, str]:
    with Session(engine) as session:
        role = session.scalar(select(Role).where(Role.name == role_name))
        assert role is not None
        username = f"audit_{role_name.lower()}"
        user = User(username=username, password_hash="not-used", real_name=username)
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()
        token = create_access_token(user_id=user.id, username=user.username)
    return {"Authorization": f"Bearer {token}"}


def test_audit_logs_return_operator_name_and_support_all_filters(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    with Session(db_engine) as session:
        operator = User(
            username="audit_operator",
            password_hash="not-used",
            real_name="审计操作员",
        )
        session.add(operator)
        session.flush()
        target_id = uuid4()
        included = AuditLog(
            operator_id=operator.id,
            action="WEIGHING_TASK_COMPLETED",
            target_type="WeighingTask",
            target_id=target_id,
            before_value={"status": "GROSS_COMPLETED"},
            after_value={"status": "COMPLETED"},
            reason=None,
            created_at=datetime(2026, 9, 16, 16, 0, tzinfo=timezone.utc),
        )
        excluded = AuditLog(
            operator_id=operator.id,
            action="BILLING_PAID",
            target_type="BillingRecord",
            target_id=uuid4(),
            before_value={"payment_status": "UNPAID"},
            after_value={"payment_status": "PAID"},
            reason=None,
            created_at=datetime(2026, 9, 16, 15, 59, tzinfo=timezone.utc),
        )
        session.add_all([included, excluded])
        session.commit()
        operator_id = operator.id
        included_id = included.id

    response = api_client.get(
        "/api/v1/audit/logs",
        params={
            "start_date": "2026-09-17",
            "end_date": "2026-09-17",
            "operator_id": str(operator_id),
            "action": "WEIGHING_TASK_COMPLETED",
            "target_type": "WeighingTask",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    item = response.json()[0]
    assert item["id"] == str(included_id)
    assert item["operator_id"] == str(operator_id)
    assert item["operator_name"] == "审计操作员"
    assert item["target_id"] == str(target_id)
    assert item["before_value"] == {"status": "GROSS_COMPLETED"}
    assert item["after_value"] == {"status": "COMPLETED"}


def test_audit_logs_return_empty_list_when_no_data(
    api_client: TestClient,
) -> None:
    response = api_client.get("/api/v1/audit/logs")

    assert response.status_code == 200
    assert response.json() == []


def test_operator_can_view_audit_logs(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    response = api_client.get(
        "/api/v1/audit/logs",
        headers=_headers_for_role(db_engine, "OPERATOR"),
    )

    assert response.status_code == 200


def test_viewer_cannot_view_audit_logs(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    response = api_client.get(
        "/api/v1/audit/logs",
        headers=_headers_for_role(db_engine, "VIEWER"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"
