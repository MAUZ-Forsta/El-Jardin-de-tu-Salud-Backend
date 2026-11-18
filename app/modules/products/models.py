import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

PHYSICAL_CATEGORIES = (
    "HERBAL_MEDICINE",
    "MEDICINAL_PLANT",
    "SUPPLEMENT",
    "HEALTHY_SNACK",
)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("kind IN ('PHYSICAL', 'COURSE')", name="ck_products_kind"),
        CheckConstraint(
            "(kind = 'PHYSICAL' AND category IN "
            "('HERBAL_MEDICINE', 'MEDICINAL_PLANT', 'SUPPLEMENT', 'HEALTHY_SNACK')) "
            "OR (kind = 'COURSE' AND category IS NULL)",
            name="ck_products_kind_category",
        ),
        CheckConstraint("price >= 0", name="ck_products_price_nonnegative"),
        Index("ix_products_public", "kind", "is_active", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    kind: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'PHYSICAL'")
    )
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    ingredients: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    properties: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_use: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
        onupdate=func.now()
    )
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.position"
    )

    @property
    def main_image_url(self) -> str:
        return self.images[0].url


class ProductImage(Base):
    __tablename__ = "product_images"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_product_images_position"),
        UniqueConstraint("product_id", "position", name="uq_product_images_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    product: Mapped[Product] = relationship(back_populates="images")
