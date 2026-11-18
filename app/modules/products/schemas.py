import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

Category = Literal[
    "HERBAL_MEDICINE", "MEDICINAL_PLANT", "SUPPLEMENT", "HEALTHY_SNACK"
]


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=200)
    description: str
    category: Category
    price: Decimal = Field(ge=0)
    images: list[HttpUrl] = Field(min_length=1)
    ingredients: str | None = None
    benefits: str | None = None
    properties: str | None = None
    suggested_use: str | None = None
    warnings: str | None = None

    @field_validator("name", "description")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío.")
        return value

    @field_validator("ingredients", "benefits", "properties", "suggested_use", "warnings")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("images")
    @classmethod
    def image_lengths(cls, images: list[HttpUrl]) -> list[HttpUrl]:
        if any(len(str(url)) > 2048 for url in images):
            raise ValueError("La URL de una imagen es demasiado larga.")
        return images


class ProductPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    category: Category | None = None
    price: Decimal | None = Field(default=None, ge=0)
    images: list[HttpUrl] | None = Field(default=None, min_length=1)
    ingredients: str | None = None
    benefits: str | None = None
    properties: str | None = None
    suggested_use: str | None = None
    warnings: str | None = None
    is_active: bool | None = None

    @field_validator("name", "description")
    @classmethod
    def required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("El campo no puede estar vacío.")
        return value

    @field_validator("ingredients", "benefits", "properties", "suggested_use", "warnings")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("images")
    @classmethod
    def image_lengths(cls, images: list[HttpUrl] | None) -> list[HttpUrl] | None:
        if images is not None and any(len(str(url)) > 2048 for url in images):
            raise ValueError("La URL de una imagen es demasiado larga.")
        return images

    @model_validator(mode="after")
    def reject_empty_or_null_required(self):
        if not self.model_fields_set:
            raise ValueError("Se requiere al menos un campo para actualizar.")
        for field in ("name", "description", "category", "price", "images", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser null.")
        return self


class ProductImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    position: int


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    category: Category
    price: Decimal
    main_image_url: str
    images: list[ProductImageOut]
    ingredients: str | None
    benefits: str | None
    properties: str | None
    suggested_use: str | None
    warnings: str | None
    stock_available: None = None


class ProductDetailOut(ProductOut):
    related_products: list[ProductOut] = Field(default_factory=list)


class ProductAdminOut(ProductOut):
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductPage(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int


class ProductAdminPage(BaseModel):
    items: list[ProductAdminOut]
    total: int
    limit: int
    offset: int
