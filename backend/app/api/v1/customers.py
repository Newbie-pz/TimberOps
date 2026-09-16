"""Customer REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.schemas.lifecycle import DeleteEntityInput
from app.security.permissions import require_permission
from app.services.customer_service import CustomerService


router = APIRouter(prefix="/customers", tags=["customers"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(data: CustomerCreate, session: DbSession) -> object:
    return CustomerService(session).create_customer(data)


@router.get("", response_model=list[CustomerRead])
def list_customers(session: DbSession) -> object:
    return CustomerService(session).list_customers()


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: UUID, session: DbSession) -> object:
    return CustomerService(session).get_customer(customer_id)


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    session: DbSession,
) -> object:
    return CustomerService(session).update_customer(customer_id, data)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_customer(
    customer_id: UUID,
    data: DeleteEntityInput,
    session: DbSession,
    current_user: Annotated[
        User,
        Depends(require_permission("customer:delete")),
    ],
) -> None:
    CustomerService(session).delete_customer(
        customer_id,
        data,
        operator_id=current_user.id,
    )
