"""Customer application service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import utc_now
from app.domain.exceptions import CustomerHasHistoryError, NotFoundError
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.models.weighing import WeighingTask
from app.schemas.lifecycle import DeleteEntityInput
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    """Manage the intentionally minimal customer record."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_customer(self, data: CustomerCreate) -> Customer:
        customer = Customer(**data.model_dump())
        self._session.add(customer)
        self._session.commit()
        self._session.refresh(customer)
        return customer

    def get_customer(self, customer_id: UUID) -> Customer:
        customer = self._session.scalar(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.deleted_at.is_(None),
            )
        )
        if customer is None:
            raise NotFoundError(f"customer not found: {customer_id}")
        return customer

    def list_customers(self) -> list[Customer]:
        """Return customers in a stable creation order for the V1 API."""
        return list(
            self._session.scalars(
                select(Customer)
                .where(Customer.deleted_at.is_(None))
                .order_by(Customer.created_at, Customer.id)
            )
        )

    def update_customer(self, customer_id: UUID, data: CustomerUpdate) -> Customer:
        customer = self.get_customer(customer_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        self._session.commit()
        self._session.refresh(customer)
        return customer

    def delete_customer(
        self,
        customer_id: UUID,
        data: DeleteEntityInput,
        *,
        operator_id: UUID | None = None,
    ) -> None:
        customer = self._session.scalar(
            select(Customer)
            .where(
                Customer.id == customer_id,
                Customer.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if customer is None:
            raise NotFoundError(f"customer not found: {customer_id}")
        history_count = self._session.scalar(
            select(func.count(WeighingTask.id)).where(
                WeighingTask.customer_id == customer_id
            )
        )
        if history_count:
            raise CustomerHasHistoryError("该客户存在历史称重记录，无法删除")

        customer.deleted_at = utc_now()
        self._session.add(
            AuditLog(
                operator_id=operator_id,
                action="CUSTOMER_DELETED",
                target_type="Customer",
                target_id=customer.id,
                before_value={"deleted_at": None},
                after_value={"deleted_at": customer.deleted_at.isoformat()},
                reason=data.reason,
            )
        )
        self._session.commit()
