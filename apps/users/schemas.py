import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBaseSchema(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr


class UserCreationSchema(UserBaseSchema):
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def _password_within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes long.")
        return value


class UserResponseSchema(UserBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class UserCreationResponseSchema(UserResponseSchema):
    """Returned from POST /users/ - same fields as UserResponseSchema today,
    kept as its own class so the create response can diverge later (e.g. to
    include a one-time field) without touching the list/get response."""
