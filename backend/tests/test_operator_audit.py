"""Authenticated operator identity and audit-trail integration tests."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.domain.enums import CargoType, VehicleType, WeightType
from app.models.audit_log import AuditLog
from app.models.billing import BillingRecord
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.models.weighing import WeighingRecord, WeighingTask
from app.schemas.vehicle import VehicleCreate
from app.schemas.weighing import (
    TareWeightInput,
    WeighingRecordRead,
    WeighingTaskCreate,
    WeighingTaskRead,
)
from app.security.jwt import create_access_token
from app.services.vehicle_service import VehicleService
from app.services.weighing_service import WeighingService


def _headers_for_role(
    engine: Engine,
    *,
    role_name: str,
    username: str,
) -> tuple[User, dict[str, str]]:
    with Session(engine, expire_on_commit=False) as session:
        role = session.scalar(select(Role).where(Role.name == role_name))
        assert role is not None
        user = User(username=username, password_hash="not-used", real_name=username)
        session.add(user)
        session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        session.commit()
        token = create_access_token(user_id=user.id, username=user.username)
        session.expunge(user)
    return user, {"Authorization": f"Bearer {token}"}


def _create_vehicle(client: TestClient, plate_number: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/vehicles",
        json={
            "plate_number": plate_number,
            "vehicle_type": "LARGE",
            "allowed_gross_weight_tons": "49.000",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_weighing_flow_preserves_each_authenticated_operator(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    user_a, headers_a = _headers_for_role(
        db_engine,
        role_name="OPERATOR",
        username="operator_a",
    )
    user_b, headers_b = _headers_for_role(
        db_engine,
        role_name="OPERATOR",
        username="operator_b",
    )
    vehicle = _create_vehicle(api_client, "蒙H91001")

    created = api_client.post(
        "/api/v1/weighing/tasks",
        json={"vehicle_id": vehicle["id"], "cargo_type": "COAL"},
        headers=headers_a,
    )
    assert created.status_code == 201
    assert created.json()["created_by"] == str(user_a.id)
    task_id = created.json()["id"]

    assert api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/tare",
        json={"weight_tons": "15.000"},
        headers=headers_a,
    ).status_code == 200
    assert api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/wait-gross",
        headers=headers_a,
    ).status_code == 200
    overweight = api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/gross",
        json={"weight_tons": "50.000"},
        headers=headers_a,
    )
    assert overweight.status_code == 200
    assert overweight.json()["weight_result"] == "OVERWEIGHT"

    reweighed = api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/reweigh",
        json={"weight_tons": "45.000", "remark": "卸货后复磅"},
        headers=headers_b,
    )
    assert reweighed.status_code == 200
    assert api_client.post(
        f"/api/v1/weighing/tasks/{task_id}/complete",
        headers=headers_a,
    ).status_code == 200

    with Session(db_engine) as session:
        task = session.get(WeighingTask, UUID(task_id))
        assert task is not None
        assert task.created_by == user_a.id
        records = list(
            session.scalars(
                select(WeighingRecord)
                .where(WeighingRecord.weighing_task_id == task.id)
                .order_by(WeighingRecord.sequence_no)
            )
        )
        assert [record.weight_type for record in records] == [
            WeightType.TARE,
            WeightType.GROSS,
            WeightType.REWEIGH,
        ]
        assert [record.recorded_by for record in records] == [
            user_a.id,
            user_a.id,
            user_b.id,
        ]
        assert session.scalar(
            select(BillingRecord).where(BillingRecord.weighing_task_id == task.id)
        ) is not None

        audit_operators = {
            audit.action: audit.operator_id
            for audit in session.scalars(
                select(AuditLog).where(AuditLog.target_id == task.id)
            )
        }
        assert audit_operators == {
            "WEIGHING_TASK_CREATED": user_a.id,
            "TARE_RECORDED": user_a.id,
            "GROSS_RECORDED": user_a.id,
            "REWEIGH_RECORDED": user_b.id,
            "WEIGHING_TASK_COMPLETED": user_a.id,
        }


def test_delete_operations_ignore_forged_operator_id(
    api_client: TestClient,
    db_engine: Engine,
) -> None:
    user_b, _ = _headers_for_role(
        db_engine,
        role_name="OPERATOR",
        username="forgery_target",
    )
    with Session(db_engine) as session:
        admin = session.scalar(select(User).where(User.username == "test_admin"))
        assert admin is not None
        admin_id = admin.id

    task_vehicle = _create_vehicle(api_client, "蒙H91002")
    task_response = api_client.post(
        "/api/v1/weighing/tasks",
        json={"vehicle_id": task_vehicle["id"], "cargo_type": "TIMBER"},
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]
    deleted_task = api_client.request(
        "DELETE",
        f"/api/v1/weighing/tasks/{task_id}",
        json={"reason": "重复任务", "operator_id": str(user_b.id)},
    )
    assert deleted_task.status_code == 204

    deletable_vehicle = _create_vehicle(api_client, "蒙H91003")
    deleted_vehicle = api_client.request(
        "DELETE",
        f"/api/v1/vehicles/{deletable_vehicle['id']}",
        json={"reason": "重复车辆", "operator_id": str(user_b.id)},
    )
    assert deleted_vehicle.status_code == 204

    customer_response = api_client.post(
        "/api/v1/customers",
        json={"name": "待删除客户"},
    )
    customer_id = customer_response.json()["id"]
    deleted_customer = api_client.request(
        "DELETE",
        f"/api/v1/customers/{customer_id}",
        json={"reason": "重复客户", "operator_id": str(user_b.id)},
    )
    assert deleted_customer.status_code == 204

    with Session(db_engine) as session:
        task = session.get(WeighingTask, UUID(task_id))
        assert task is not None
        assert task.deleted_by == admin_id
        assert task.delete_reason == "重复任务"
        audits = list(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.action.in_(
                        [
                            "WEIGHING_TASK_DELETED",
                            "VEHICLE_DELETED",
                            "CUSTOMER_DELETED",
                        ]
                    )
                )
            )
        )
        assert len(audits) == 3
        assert {audit.operator_id for audit in audits} == {admin_id}
        assert user_b.id not in {audit.operator_id for audit in audits}


def test_historical_null_operator_records_remain_readable(
    db_session: Session,
) -> None:
    vehicle = VehicleService(db_session).create_vehicle(
        VehicleCreate(
            plate_number="蒙H91004",
            vehicle_type=VehicleType.LARGE,
            allowed_gross_weight_tons=Decimal("49.000"),
        )
    )
    service = WeighingService(db_session)
    task = service.create_task(
        WeighingTaskCreate(
            vehicle_id=vehicle.id,
            cargo_type=CargoType.TIMBER,
        )
    )
    service.record_tare(
        task.id,
        TareWeightInput(weight_tons=Decimal("15.000")),
    )

    assert task.created_by is None
    records = service.list_records(task.id)
    assert len(records) == 1
    assert records[0].recorded_by is None
    assert WeighingTaskRead.model_validate(task).created_by is None
    assert WeighingRecordRead.model_validate(records[0]).recorded_by is None
