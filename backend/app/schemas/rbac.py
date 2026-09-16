"""RBAC read models and role-assignment commands."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    created_at: datetime


class UserRoleAssign(BaseModel):
    role_id: UUID


class UserRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    role_id: UUID
