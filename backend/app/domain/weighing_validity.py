"""Shared SQL predicate for business-valid (not reversed) weighing tasks."""

from typing import Any

from sqlalchemy import exists, select

from app.models.weighing_reversal import WeighingReversal


def task_is_not_reversed(task_id: Any) -> Any:
    """Return a correlated predicate reused by every operating aggregation."""
    return ~exists(
        select(WeighingReversal.id).where(
            WeighingReversal.original_task_id == task_id
        )
    )
