"""Read-only queries for the append-only audit trail."""

from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.exceptions import BusinessRuleError
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead


UTC_PLUS_8 = timezone(timedelta(hours=8))


class AuditService:
    """Expose filtered audit history without mutating audit or business data."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_logs(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        operator_id: UUID | None = None,
        action: str | None = None,
        target_type: str | None = None,
    ) -> list[AuditLogRead]:
        """Query audit events with inclusive UTC+8 calendar-date filters."""
        if (
            start_date is not None
            and end_date is not None
            and start_date > end_date
        ):
            raise BusinessRuleError("start_date must be on or before end_date")

        statement = select(AuditLog, User.real_name).outerjoin(
            User,
            User.id == AuditLog.operator_id,
        )
        if start_date is not None:
            statement = statement.where(
                AuditLog.created_at >= self._local_day_start_utc(start_date)
            )
        if end_date is not None:
            statement = statement.where(
                AuditLog.created_at
                < self._local_day_start_utc(end_date + timedelta(days=1))
            )
        if operator_id is not None:
            statement = statement.where(AuditLog.operator_id == operator_id)
        if action is not None:
            statement = statement.where(AuditLog.action == action)
        if target_type is not None:
            statement = statement.where(AuditLog.target_type == target_type)

        rows = self._session.execute(
            statement.order_by(AuditLog.created_at.desc(), AuditLog.id)
        ).all()
        return [
            AuditLogRead(
                id=log.id,
                operator_id=log.operator_id,
                operator_name=operator_name,
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                reason=log.reason,
                before_value=log.before_value,
                after_value=log.after_value,
                created_at=log.created_at,
            )
            for log, operator_name in rows
        ]

    @staticmethod
    def _local_day_start_utc(value: date) -> datetime:
        local_start = datetime.combine(value, time.min, tzinfo=UTC_PLUS_8)
        return local_start.astimezone(timezone.utc)
