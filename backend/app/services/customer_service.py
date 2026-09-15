"""Customer application service."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.exceptions import NotFoundError
from app.models.customer import Customer
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
        customer = self._session.get(Customer, customer_id)
        if customer is None:
            raise NotFoundError(f"customer not found: {customer_id}")
        return customer

    def update_customer(self, customer_id: UUID, data: CustomerUpdate) -> Customer:
        customer = self.get_customer(customer_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        self._session.commit()
        self._session.refresh(customer)
        return customer
