"""Deterministic weighbridge simulator for development, CI, and demos."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from threading import Lock

from app.integrations.weighbridge.base import (
    DeviceOfflineError,
    DeviceReadError,
    DeviceStatus,
    DeviceTimeoutError,
    InvalidWeightError,
    WeighbridgeAdapter,
    WeighbridgeStatus,
    WeightReading,
)


class SimulatedWeighbridgeAdapter(WeighbridgeAdapter):
    """Yield configured readings in order, then keep returning the final value."""

    mode = "simulator"

    def __init__(
        self,
        *,
        weights: tuple[Decimal, ...],
        stable: bool = True,
        device_status: DeviceStatus = DeviceStatus.ONLINE,
    ) -> None:
        if not weights:
            raise ValueError("simulator requires at least one configured weight")
        self._weights = weights
        self._stable = stable
        self._device_status = device_status
        self._index = 0
        self._lock = Lock()

    def get_status(self) -> WeighbridgeStatus:
        available = self._device_status is DeviceStatus.ONLINE
        messages = {
            DeviceStatus.ONLINE: "模拟地磅在线",
            DeviceStatus.OFFLINE: "模拟地磅离线",
            DeviceStatus.TIMEOUT: "模拟地磅读取超时",
            DeviceStatus.ERROR: "模拟地磅读取异常",
            DeviceStatus.MANUAL: "人工称重模式",
        }
        return WeighbridgeStatus(
            mode=self.mode,
            device_status=self._device_status,
            available=available,
            message=messages[self._device_status],
        )

    def read_weight(self) -> WeightReading:
        if self._device_status is DeviceStatus.OFFLINE:
            raise DeviceOfflineError("地磅设备当前离线")
        if self._device_status is DeviceStatus.TIMEOUT:
            raise DeviceTimeoutError("地磅设备读取超时")
        if self._device_status is DeviceStatus.ERROR:
            raise DeviceReadError("地磅设备返回读取错误")
        if self._device_status is not DeviceStatus.ONLINE:
            raise DeviceReadError("地磅设备状态不可读取")

        with self._lock:
            weight = self._weights[min(self._index, len(self._weights) - 1)]
            if self._index < len(self._weights) - 1:
                self._index += 1
        if (
            not weight.is_finite()
            or weight <= 0
            or weight > Decimal("9999999.999")
        ):
            raise InvalidWeightError("地磅读数必须是大于零的有限数值")
        try:
            normalized_weight = weight.quantize(Decimal("0.001"))
        except InvalidOperation as exc:
            raise InvalidWeightError("地磅读数精度或范围无效") from exc
        return WeightReading(
            weight=normalized_weight,
            unit="t",
            stable=self._stable,
            timestamp=datetime.now(timezone.utc),
            device_status=DeviceStatus.ONLINE,
        )
