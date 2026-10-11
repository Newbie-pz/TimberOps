"""Manual-mode adapter preserving operator-entered weighing as the default."""

from app.integrations.weighbridge.base import (
    DeviceStatus,
    ManualModeError,
    WeighbridgeAdapter,
    WeighbridgeStatus,
    WeightReading,
)


class ManualWeighbridgeAdapter(WeighbridgeAdapter):
    """Explicitly represents deployments with no configured device reader."""

    mode = "manual"

    def read_weight(self) -> WeightReading:
        raise ManualModeError("当前为人工称重模式，请手动输入重量")

    def get_status(self) -> WeighbridgeStatus:
        return WeighbridgeStatus(
            mode=self.mode,
            device_status=DeviceStatus.MANUAL,
            available=False,
            message="人工称重模式",
        )
