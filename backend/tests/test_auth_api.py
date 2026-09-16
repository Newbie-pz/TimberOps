"""Authentication API integration tests."""

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


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
    response = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": ""},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_with_invalid_token_is_rejected(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


def test_public_registration_enabled_keeps_register_available(
    api_client: TestClient,
) -> None:
    settings = Settings(PUBLIC_REGISTRATION_ENABLED=True)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = api_client.post(
            "/api/v1/auth/register",
            json={**REGISTER_PAYLOAD, "username": "enabled_registration"},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 201


def test_registration_switch_does_not_disable_login_or_me(
    api_client: TestClient,
) -> None:
    registered = api_client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "username": "switch_user"},
    ).json()
    settings = Settings(PUBLIC_REGISTRATION_ENABLED=False)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        disabled = api_client.post(
            "/api/v1/auth/register",
            json={**REGISTER_PAYLOAD, "username": "blocked_registration"},
        )
        login = api_client.post(
            "/api/v1/auth/login",
            json={
                "username": "switch_user",
                "password": REGISTER_PAYLOAD["password"],
            },
        )
        me = api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert disabled.status_code == 403
    assert disabled.json() == {
        "error": {
            "code": "REGISTRATION_DISABLED",
            "message": "Public registration is disabled",
        }
    }
    assert login.status_code == 200
    assert me.status_code == 200
    assert me.json()["id"] == registered["id"]
