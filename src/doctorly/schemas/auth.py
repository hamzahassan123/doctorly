from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field, SecretStr

from doctorly.models import UserRole
from doctorly.schemas.common import ApiSchema


class UserRegister(ApiSchema):
    email: EmailStr
    password: SecretStr = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    phone_number: str | None = Field(default=None, max_length=32)


class LoginRequest(ApiSchema):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class UserRead(ApiSchema):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime


class AccessTokenRead(ApiSchema):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
