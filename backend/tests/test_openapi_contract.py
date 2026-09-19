"""Documentation-facing OpenAPI contract checks."""

from app.main import app


def test_openapi_metadata_and_business_groups_are_stable() -> None:
    schema = app.openapi()

    assert schema["info"]["title"] == app.title
    assert schema["info"]["version"] == "0.7.0"
    assert {tag["name"] for tag in schema["tags"]} == {
        "Auth",
        "Users / RBAC",
        "Vehicles",
        "Customers",
        "Weighing",
        "Billing",
        "Dashboard",
        "Reports",
        "Audit",
        "Export",
        "AI",
        "System / Observability",
    }


def test_openapi_contains_documented_operational_paths_and_summaries() -> None:
    paths = app.openapi()["paths"]

    documented_paths = {
        "/api/v1/ai/chat",
        "/api/v1/audit/logs",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/auth/permissions",
        "/api/v1/auth/register",
        "/api/v1/auth/registration-status",
        "/api/v1/auth/roles",
        "/api/v1/billing/records",
        "/api/v1/billing/records/{record_id}/pay",
        "/api/v1/billing/records/{record_id}/waive",
        "/api/v1/customers",
        "/api/v1/customers/{customer_id}",
        "/api/v1/dashboard/overview",
        "/api/v1/export/weighing",
        "/api/v1/reports/daily",
        "/api/v1/reports/export",
        "/api/v1/reports/monthly",
        "/api/v1/users",
        "/api/v1/users/roles",
        "/api/v1/users/{user_id}/roles",
        "/api/v1/users/{user_id}/roles/{role_id}",
        "/api/v1/vehicles",
        "/api/v1/vehicles/{vehicle_id}",
        "/api/v1/weighing/cargo-catalog",
        "/api/v1/weighing/tasks",
        "/api/v1/weighing/tasks/{task_id}",
        "/api/v1/weighing/tasks/{task_id}/complete",
        "/api/v1/weighing/tasks/{task_id}/gross",
        "/api/v1/weighing/tasks/{task_id}/loading",
        "/api/v1/weighing/tasks/{task_id}/records",
        "/api/v1/weighing/tasks/{task_id}/reweigh",
        "/api/v1/weighing/tasks/{task_id}/tare",
        "/api/v1/weighing/tasks/{task_id}/wait-gross",
        "/health",
        "/metrics",
        "/ready",
    }

    assert set(paths) == documented_paths

    assert paths["/api/v1/auth/login"]["post"]["summary"] == (
        "Issue a JWT access token"
    )
    assert paths["/api/v1/weighing/tasks"]["post"]["summary"] == (
        "Create a weighing task"
    )
    assert paths["/api/v1/billing/records/{record_id}/waive"]["patch"][
        "summary"
    ] == "Waive a fee"
    assert paths["/api/v1/dashboard/overview"]["get"]["summary"]
    assert paths["/api/v1/reports/export"]["get"]["summary"]
    assert paths["/api/v1/audit/logs"]["get"]["summary"]
    assert paths["/api/v1/ai/chat"]["post"]["summary"]
    assert {"/health", "/ready", "/metrics"} <= set(paths)
