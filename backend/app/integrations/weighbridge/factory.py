"""Configuration-driven weighbridge adapter construction."""

from decimal import Decimal

from app.core.config import Settings
from app.integrations.weighbridge.base import DeviceStatus, WeighbridgeAdapter
from app.integrations.weighbridge.manual import ManualWeighbridgeAdapter
from app.integrations.weighbridge.simulator import SimulatedWeighbridgeAdapter


def create_weighbridge_adapter(settings: Settings) -> WeighbridgeAdapter:
    """Build one process-local adapter from validated runtime configuration."""
    if settings.weighbridge_mode == "manual":
        return ManualWeighbridgeAdapter()
    weights = tuple(
        Decimal(part.strip())
        for part in settings.weighbridge_simulator_weights.split(",")
    )
    return SimulatedWeighbridgeAdapter(
        weights=weights,
        stable=settings.weighbridge_simulator_stable,
        device_status=DeviceStatus(settings.weighbridge_simulator_status),
    )
