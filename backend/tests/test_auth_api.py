"""Authentication API integration tests."""

from fastapi.testclient import TestClient


REGISTER_PAYLOAD = {
    "username": "ScaleOperator",
    "password": "TimberOps-Secret-123!",
    "real_name": "磅房操作员",
}


def test_register_creates_user_without_exposing_password_hash(
    api_client: TestClient,
) -> None:
    response = api_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "scaleoperator"
    assert body["real_name"] == "磅房操作员"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body


def test_register_rejects_duplicate_username(api_client: TestClient) -> None:
    assert api_client.post(
        "/api/v1/auth/register", json=REGISTER_PAYLOAD
    ).status_code == 201

    duplicate = api_client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "username": "SCALEOPERATOR"},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "BUSINESS_CONFLICT"


def test_login_with_correct_password_returns_bearer_token(
    api_client: TestClient,
) -> None:
    api_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = api_client.post(
        "/api/v1/auth/login",
        json={
            "username": REGISTER_PAYLOAD["username"],
            "password": REGISTER_PAYLOAD["password"],
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "Bearer"
    assert response.json()["expires_in"] == 3600
    assert response.json()["access_token"]


def test_login_with_wrong_password_is_rejected(api_client: TestClient) -> None:
    api_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": REGISTER_PAYLOAD["username"], "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_me_with_valid_token_returns_current_user(api_client: TestClient) -> None:
    registered = api_client.post(
        "/api/v1/auth/register", json=REGISTER_PAYLOAD
    ).json()
    token = api_client.post(
        "/api/v1/auth/login",
        json={
            "username": REGISTER_PAYLOAD["username"],
            "password": REGISTER_PAYLOAD["password"],
        },
    ).json()["access_token"]

    response = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == registered["id"]
    assert "password_hash" not in response.json()


def test_me_without_token_is_rejected(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_invalid_token_is_rejected(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
