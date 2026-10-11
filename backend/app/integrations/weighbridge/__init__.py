"""Weighbridge hardware boundary and deterministic development adapters."""

from app.integrations.weighbridge.base import (
    DeviceStatus,
    WeighbridgeAdapter,
    WeighbridgeStatus,
    WeightReading,
)
from app.integrations.weighbridge.factory import create_weighbridge_adapter
from app.integrations.weighbridge.manual import ManualWeighbridgeAdapter
from app.integrations.weighbridge.simulator import SimulatedWeighbridgeAdapter

__all__ = [
    "DeviceStatus",
    "ManualWeighbridgeAdapter",
    "SimulatedWeighbridgeAdapter",
    "WeightReading",
    "WeighbridgeAdapter",
    "WeighbridgeStatus",
    "create_weighbridge_adapter",
]
