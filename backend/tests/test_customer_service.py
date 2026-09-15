"""Minimal customer service tests."""

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.customer_service import CustomerService


def test_create_and_get_customer(db_session: Session) -> None:
    service = CustomerService(db_session)
    customer = service.create_customer(
        CustomerCreate(name="北方运输有限公司", contact_name="李经理")
    )

    loaded = service.get_customer(customer.id)
    assert loaded.name == "北方运输有限公司"
    assert loaded.contact_name == "李经理"


def test_customer_update_rejects_null_name() -> None:
    with pytest.raises(PydanticValidationError):
        CustomerUpdate.model_validate({"name": None})
