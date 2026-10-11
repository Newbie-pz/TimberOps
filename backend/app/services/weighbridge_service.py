"""Safe orchestration and observability for read-only weighbridge access."""

import json
import logging
from time import perf_counter

from app.integrations.weighbridge.base import (
    WeighbridgeAdapter,
    WeighbridgeError,
    WeighbridgeStatus,
    WeightReading,
)
from app.observability.metrics import (
    observe_weighbridge_read,
    set_weighbridge_online,
)

logger = logging.getLogger("timberops.weighbridge")


class WeighbridgeService:
    """Read an adapter without coupling device availability to business health."""

    def __init__(self, adapter: WeighbridgeAdapter) -> None:
        self._adapter = adapter

    def get_status(self) -> WeighbridgeStatus:
        status = self._adapter.get_status()
        set_weighbridge_online(
            adapter=self._adapter.mode,
            online=status.available,
        )
        return status

    def read_weight(self) -> WeightReading:
        started_at = perf_counter()
        outcome = "success"
        try:
            reading = self._adapter.read_weight()
            set_weighbridge_online(adapter=self._adapter.mode, online=True)
            return reading
        except WeighbridgeError as exc:
            outcome = exc.code.removeprefix("WEIGHBRIDGE_").lower()
            set_weighbridge_online(adapter=self._adapter.mode, online=False)
            raise
        finally:
            latency = max(perf_counter() - started_at, 0.0)
            observe_weighbridge_read(
                adapter=self._adapter.mode,
                status=outcome,
            )
            logger.info(
                json.dumps(
                    {
                        "event": "weighbridge_read",
                        "adapter": self._adapter.mode,
                        "status": outcome,
                        "latency_ms": round(latency * 1000, 2),
                    },
                    separators=(",", ":"),
                )
            )
