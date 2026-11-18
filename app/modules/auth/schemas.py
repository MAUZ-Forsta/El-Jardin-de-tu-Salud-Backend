
import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class RegisterRequest(BaseModel):
    """Datos necesarios para registrar un cliente."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(
        min_length=12,
        max_length=128,
    )

    first_name: str = Field(
        min_length=1,
        max_length=100,
    )

    middle_name: str | None = Field(
        default=None,
        max_length=100,
    )

    last_name: str = Field(
        min_length=1,
        max_length=100,
    )

    second_last_name: str | None = Field(
        default=None,
        max_length=100,
    )

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_required_names(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "El campo no puede estar vacío."
            )

        return value

    @field_validator("middle_name", "second_last_name")
    @classmethod
    def normalize_optional_names(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        return value.strip() or None


class UserResponse(BaseModel):
    """Datos públicos del usuario registrado."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class RegisterResponse(BaseModel):
    """Respuesta de un registro exitoso."""

    user: UserResponse
    message: str = "Cuenta registrada correctamente."
