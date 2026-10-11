"""Vendor-neutral contract for reading a weighbridge without business writes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal


class DeviceStatus(StrEnum):
    """Bounded operational states shared by adapters and observability."""

    MANUAL = "manual"
    ONLINE = "online"
    OFFLINE = "offline"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass(frozen=True)
class WeighbridgeStatus:
    """Current adapter capability without triggering a weight read."""

    mode: Literal["manual", "simulator"]
    device_status: DeviceStatus
    available: bool
    message: str


@dataclass(frozen=True)
class WeightReading:
    """One transient device observation; it is not a business record."""

    weight: Decimal
    unit: Literal["t"]
    stable: bool
    timestamp: datetime
    device_status: DeviceStatus


class WeighbridgeError(Exception):
    """Base class for expected adapter failures with a stable API code."""

    code = "WEIGHBRIDGE_ERROR"


class ManualModeError(WeighbridgeError):
    code = "WEIGHBRIDGE_MANUAL_MODE"


class DeviceOfflineError(WeighbridgeError):
    code = "WEIGHBRIDGE_OFFLINE"


class DeviceTimeoutError(WeighbridgeError):
    code = "WEIGHBRIDGE_TIMEOUT"


class DeviceReadError(WeighbridgeError):
    code = "WEIGHBRIDGE_READ_ERROR"


class InvalidWeightError(DeviceReadError):
    code = "WEIGHBRIDGE_INVALID_WEIGHT"


class WeighbridgeAdapter(ABC):
    """Small extension point for future vendor-specific Serial/TCP adapters."""

    mode: Literal["manual", "simulator"]

    @abstractmethod
    def read_weight(self) -> WeightReading:
        """Return one validated observation or raise a typed adapter error."""

    @abstractmethod
    def get_status(self) -> WeighbridgeStatus:
        """Return device capability without writing application state."""
