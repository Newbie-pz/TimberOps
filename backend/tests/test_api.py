"""Phase 1.3 REST API integration tests."""

from typing import Any

from fastapi.testclient import TestClient


def create_vehicle(
    client: TestClient,
    *,
    plate_number: str = "蒙H12345",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/vehicles",
        json={
            "plate_number": plate_number,
            "driver_name": "张师傅",
            "vehicle_type": "LARGE",
            "allowed_gross_weight_tons": "49.000",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_task(
    client: TestClient,
    vehicle_id: str,
    *,
    cargo_type: str = "COAL",
) -> dict[str, Any]:
    response = client.post(
        "/api/v1/weighing/tasks",
        json={"vehicle_id": vehicle_id, "cargo_type": cargo_type},
    )
    assert response.status_code == 201
    return response.json()


def advance_to_wait_gross(client: TestClient, task_id: str) -> None:
    tare = client.post(
        f"/api/v1/weighing/tasks/{task_id}/tare",
        json={"weight_tons": "15.820"},
    )
    assert tare.status_code == 200
    assert tare.json()["status"] == "TARE_COMPLETED"
    assert client.post(
        f"/api/v1/weighing/tasks/{task_id}/wait-gross"
    ).json()["status"] == "WAIT_GROSS"


def test_create_list_get_and_update_vehicle_api(api_client: TestClient) -> None:
    vehicle = create_vehicle(api_client)

    assert api_client.get("/api/v1/vehicles").json()[0]["id"] == vehicle["id"]
    assert api_client.get(
        f"/api/v1/vehicles/{vehicle['id']}"
    ).status_code == 200

    response = api_client.patch(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"driver_name": "李师傅", "allowed_gross_weight_tons": "48.500"},
    )
    assert response.status_code == 200
    assert response.json()["driver_name"] == "李师傅"
    assert response.json()["allowed_gross_weight_tons"] == "48.500"


def test_duplicate_vehicle_plate_returns_business_conflict(
    api_client: TestClient,
) -> None:
    create_vehicle(api_client)
    response = api_client.post(
        "/api/v1/vehicles",
        json={
            "plate_number": "蒙H12345",
            "vehicle_type": "LARGE",
            "allowed_gross_weight_tons": "49.000",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_CONFLICT"


def test_customer_crud_api(api_client: TestClient) -> None:
    created = api_client.post(
        "/api/v1/customers",
        json={"name": "北方运输有限公司", "contact_name": "李经理"},
    )
    assert created.status_code == 201
    customer = created.json()

    assert api_client.get("/api/v1/customers").json()[0]["id"] == customer["id"]
    updated = api_client.patch(
        f"/api/v1/customers/{customer['id']}",
        json={"phone": "13800000000"},
    )
    assert updated.status_code == 200
    assert updated.json()["phone"] == "13800000000"


def test_missing_resource_uses_error_envelope(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/vehicles/00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_create_and_filter_weighing_tasks(api_client: TestClient) -> None:
    vehicle = create_vehicle(api_client)
    task = create_task(api_client, vehicle["id"])

    assert task["status"] == "WAIT_TARE"
    assert task["weight_result"] == "PENDING"
    assert task["allowed_gross_weight_tons"] == "49.000"

    response = api_client.get(
        "/api/v1/weighing/tasks",
        params={
            "cargo_type": "COAL",
            "status": "WAIT_TARE",
            "vehicle_id": vehicle["id"],
        },
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [task["id"]]


def test_history_response_contains_cargo_name_and_remark(
    api_client: TestClient,
) -> None:
    vehicle = create_vehicle(api_client)
    created = api_client.post(
        "/api/v1/weighing/tasks",
        json={
            "vehicle_id": vehicle["id"],
            "cargo_type": "TIMBER",
            "cargo_name": "落叶松原木",
            "cargo_remark": "俄罗斯进口",
        },
    )
    assert created.status_code == 201

    history = api_client.get("/api/v1/weighing/tasks")

    assert history.status_code == 200
    assert history.json()[0]["cargo_name"] == "落叶松原木"
    assert history.json()[0]["cargo_remark"] == "俄罗斯进口"


def test_legacy_loading_endpoint_moves_directly_to_wait_gross(
    api_client: TestClient,
) -> None:
    vehicle = create_vehicle(api_client)
    task = create_task(api_client, vehicle["id"])
    api_client.post(
        f"/api/v1/weighing/tasks/{task['id']}/tare",
        json={"weight_tons": "15.820"},
    )

    loading = api_client.post(f"/api/v1/weighing/tasks/{task['id']}/loading")
    repeated = api_client.post(
        f"/api/v1/weighing/tasks/{task['id']}/wait-gross"
    )

    assert loading.status_code == 200
    assert loading.json()["status"] == "WAIT_GROSS"
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "WAIT_GROSS"


def test_gross_before_tare_returns_invalid_state(api_client: TestClient) -> None:
    vehicle = create_vehicle(api_client)
    task = create_task(api_client, vehicle["id"])

    response = api_client.post(
        f"/api/v1/weighing/tasks/{task['id']}/gross",
        json={"weight_tons": "47.360"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE"


def test_normal_weighing_api_flow(api_client: TestClient) -> None:
    vehicle = create_vehicle(api_client)
    task = create_task(api_client, vehicle["id"], cargo_type="TIMBER")
    advance_to_wait_gross(api_client, task["id"])

    gross = api_client.post(
        f"/api/v1/weighing/tasks/{task['id']}/gross",
        json={"weight_tons": "47.360"},
    )
    assert gross.status_code == 200
    assert gross.json()["net_weight_tons"] == "31.540"
    assert gross.json()["weight_result"] == "NORMAL"

    completed = api_client.post(
        f"/api/v1/weighing/tasks/{task['id']}/complete"
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"


def test_swagger_equivalent_overweight_reweigh_flow(
    api_client: TestClient,
) -> None:
    vehicle = create_vehicle(api_client)
    task = create_task(api_client, vehicle["id"])
    advance_to_wait_gross(api_client, task["id"])

    overweight = api_client.post(
        f"/api/v1/weighing/tasks/{task['id']}/gross",
        json={"weight_tons": "50.200"},
    )
    assert overweight.status_code == 200
    assert overweight.json()["status"] == "WAIT_GROSS"
    assert overweight.json()["weight_result"] == "OVERWEIGHT"
    assert overweight.json()["overweight_tons"] == "1.200"

    blocked = api_client.post(
        f"/api/v1/weighing/tasks/{task['id']}/complete"
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "BUSINESS_CONFLICT"

    reweigh = api_client.post(
        f"/api/v1/weighing/tasks/{task['id']}/reweigh",
        json={"weight_tons": "48.600", "remark": "卸货后重新称重"},
    )
    assert reweigh.status_code == 200
    assert reweigh.json()["status"] == "GROSS_COMPLETED"
    assert reweigh.json()["weight_result"] == "NORMAL"
    assert reweigh.json()["net_weight_tons"] == "32.780"

    completed = api_client.post(
        f"/api/v1/weighing/tasks/{task['id']}/complete"
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"

    detail = api_client.get(f"/api/v1/weighing/tasks/{task['id']}")
    assert detail.status_code == 200
    records = detail.json()["records"]
    assert [record["weight_type"] for record in records] == [
        "TARE",
        "GROSS",
        "REWEIGH",
    ]
    assert [record["sequence_no"] for record in records] == [1, 2, 3]

    history = api_client.get(
        f"/api/v1/weighing/tasks/{task['id']}/records"
    )
    assert history.status_code == 200
    assert history.json() == records


def test_reweigh_blank_remark_remains_request_validation_error(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/api/v1/weighing/tasks/00000000-0000-0000-0000-000000000001/reweigh",
        json={"weight_tons": "48.600", "remark": "   "},
    )
    assert response.status_code == 422


def test_openapi_exposes_phase_13_routes(api_client: TestClient) -> None:
    paths = api_client.get("/openapi.json").json()["paths"]
    expected = {
        "/api/v1/vehicles",
        "/api/v1/vehicles/{vehicle_id}",
        "/api/v1/customers",
        "/api/v1/customers/{customer_id}",
        "/api/v1/weighing/tasks",
        "/api/v1/weighing/tasks/{task_id}",
        "/api/v1/weighing/tasks/{task_id}/records",
        "/api/v1/weighing/tasks/{task_id}/tare",
        "/api/v1/weighing/tasks/{task_id}/loading",
        "/api/v1/weighing/tasks/{task_id}/wait-gross",
        "/api/v1/weighing/tasks/{task_id}/gross",
        "/api/v1/weighing/tasks/{task_id}/reweigh",
        "/api/v1/weighing/tasks/{task_id}/complete",
    }
    assert expected <= set(paths)
