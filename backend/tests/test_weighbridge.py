"""Weighbridge adapter, degradation, auth, and read-only API tests."""

import logging
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.v1.weighbridge import get_weighbridge_adapter
from app.core.config import Settings
from app.integrations.weighbridge.base import (
    DeviceOfflineError,
    DeviceReadError,
    DeviceStatus,
    DeviceTimeoutError,
    InvalidWeightError,
    ManualModeError,
)
from app.integrations.weighbridge.factory import create_weighbridge_adapter
from app.integrations.weighbridge.manual import ManualWeighbridgeAdapter
from app.integrations.weighbridge.simulator import SimulatedWeighbridgeAdapter
from app.main import app
from app.observability.metrics import METRICS_REGISTRY
from app.services.weighbridge_service import WeighbridgeService


def test_manual_mode_preserves_manual_input_boundary() -> None:
    adapter = ManualWeighbridgeAdapter()

    status = adapter.get_status()

    assert status.mode == "manual"
    assert status.device_status is DeviceStatus.MANUAL
    assert status.available is False
    with pytest.raises(ManualModeError):
        adapter.read_weight()


def test_factory_defaults_to_manual_and_builds_configured_simulator() -> None:
    manual = create_weighbridge_adapter(Settings(APP_ENV="test"))
    simulator = create_weighbridge_adapter(
        Settings(
            APP_ENV="test",
            WEIGHBRIDGE_MODE="simulator",
            WEIGHBRIDGE_SIMULATOR_WEIGHTS="12.100,12.200",
            WEIGHBRIDGE_SIMULATOR_STABLE=False,
        )
    )

    assert isinstance(manual, ManualWeighbridgeAdapter)
    assert isinstance(simulator, SimulatedWeighbridgeAdapter)
    assert simulator.read_weight().weight == Decimal("12.100")
    assert simulator.read_weight().stable is False


@pytest.mark.parametrize("stable", [True, False])
def test_simulator_returns_stable_or_unstable_decimal_reading(stable: bool) -> None:
    adapter = SimulatedWeighbridgeAdapter(
        weights=(Decimal("48.120"), Decimal("48.123")),
        stable=stable,
    )

    first = adapter.read_weight()
    second = adapter.read_weight()
    repeated = adapter.read_weight()

    assert first.weight == Decimal("48.120")
    assert second.weight == Decimal("48.123")
    assert repeated.weight == Decimal("48.123")
    assert first.stable is stable
    assert first.unit == "t"
    assert first.device_status is DeviceStatus.ONLINE


@pytest.mark.parametrize(
    ("device_status", "error_type"),
    [
        (DeviceStatus.OFFLINE, DeviceOfflineError),
        (DeviceStatus.TIMEOUT, DeviceTimeoutError),
        (DeviceStatus.ERROR, DeviceReadError),
    ],
)
def test_simulator_failure_modes_are_immediate_and_typed(
    device_status: DeviceStatus,
    error_type: type[Exception],
) -> None:
    adapter = SimulatedWeighbridgeAdapter(
        weights=(Decimal("32.418"),),
        device_status=device_status,
    )

    assert adapter.get_status().available is False
    with pytest.raises(error_type):
        adapter.read_weight()


@pytest.mark.parametrize(
    "weight",
    [Decimal("0"), Decimal("-1"), Decimal("NaN"), Decimal("1e100")],
)
def test_simulator_rejects_invalid_weight(weight: Decimal) -> None:
    adapter = SimulatedWeighbridgeAdapter(weights=(weight,))

    with pytest.raises(InvalidWeightError):
        adapter.read_weight()


def test_observability_does_not_log_weight_or_business_identifiers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    adapter = SimulatedWeighbridgeAdapter(weights=(Decimal("71.234"),))

    with caplog.at_level(logging.INFO, logger="timberops.weighbridge"):
        WeighbridgeService(adapter).read_weight()

    log_output = caplog.text
    assert "weighbridge_read" in log_output
    for sensitive_value in ("71.234", "plate", "task_id", "user_id"):
        assert sensitive_value not in log_output


def test_weighbridge_api_requires_authentication(api_client: TestClient) -> None:
    api_client.headers.pop("Authorization")

    status_response = api_client.get("/api/v1/weighbridge/status")
    weight_response = api_client.get("/api/v1/weighbridge/weight")

    assert status_response.status_code == 401
    assert weight_response.status_code == 401


def test_authorized_simulator_api_returns_structured_decimal_reading(
    api_client: TestClient,
) -> None:
    adapter = SimulatedWeighbridgeAdapter(
        weights=(Decimal("32.418"),),
        stable=True,
    )
    before = float(
        METRICS_REGISTRY.get_sample_value(
            "timberops_weighbridge_reads_total",
            {"adapter": "simulator", "status": "success"},
        )
        or 0
    )
    app.dependency_overrides[get_weighbridge_adapter] = lambda: adapter
    try:
        status_response = api_client.get("/api/v1/weighbridge/status")
        weight_response = api_client.get("/api/v1/weighbridge/weight")
    finally:
        app.dependency_overrides.pop(get_weighbridge_adapter, None)

    assert status_response.status_code == 200
    assert status_response.json() == {
        "mode": "simulator",
        "device_status": "online",
        "available": True,
        "message": "模拟地磅在线",
    }
    assert weight_response.status_code == 200
    assert weight_response.json()["weight"] == "32.418"
    assert weight_response.json()["unit"] == "t"
    assert weight_response.json()["stable"] is True
    assert weight_response.json()["device_status"] == "online"
    after = float(
        METRICS_REGISTRY.get_sample_value(
            "timberops_weighbridge_reads_total",
            {"adapter": "simulator", "status": "success"},
        )
        or 0
    )
    assert after == before + 1


@pytest.mark.parametrize(
    ("adapter", "status_code", "code"),
    [
        (ManualWeighbridgeAdapter(), 409, "WEIGHBRIDGE_MANUAL_MODE"),
        (
            SimulatedWeighbridgeAdapter(
                weights=(Decimal("32.418"),),
                device_status=DeviceStatus.OFFLINE,
            ),
            503,
            "WEIGHBRIDGE_OFFLINE",
        ),
        (
            SimulatedWeighbridgeAdapter(
                weights=(Decimal("32.418"),),
                device_status=DeviceStatus.TIMEOUT,
            ),
            504,
            "WEIGHBRIDGE_TIMEOUT",
        ),
    ],
)
def test_weight_api_returns_stable_degradation_errors(
    api_client: TestClient,
    adapter: object,
    status_code: int,
    code: str,
) -> None:
    app.dependency_overrides[get_weighbridge_adapter] = lambda: adapter
    try:
        response = api_client.get("/api/v1/weighbridge/weight")
    finally:
        app.dependency_overrides.pop(get_weighbridge_adapter, None)

    assert response.status_code == status_code
    assert response.json()["error"]["code"] == code


def test_device_offline_does_not_change_liveness(api_client: TestClient) -> None:
    app.dependency_overrides[get_weighbridge_adapter] = lambda: (
        SimulatedWeighbridgeAdapter(
            weights=(Decimal("32.418"),),
            device_status=DeviceStatus.OFFLINE,
        )
    )
    try:
        response = api_client.get("/health")
    finally:
        app.dependency_overrides.pop(get_weighbridge_adapter, None)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
