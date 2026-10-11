"""Public schemas for transient, read-only weighbridge observations."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.integrations.weighbridge.base import DeviceStatus


class WeighbridgeStatusRead(BaseModel):
    """Configured adapter mode and current degraded-capability state."""

    model_config = ConfigDict(from_attributes=True)

    mode: Literal["manual", "simulator"]
    device_status: DeviceStatus
    available: bool
    message: str


class WeightReadingRead(BaseModel):
    """A device reading that has not been submitted to a weighing task."""

    model_config = ConfigDict(from_attributes=True)

    weight: Decimal
    unit: Literal["t"]
    stable: bool
    timestamp: datetime
    device_status: DeviceStatus
