import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import (
    ProductAdminOut,
    ProductAdminPage,
    ProductCreate,
    ProductDetailOut,
    ProductOut,
    ProductPage,
    ProductPatch,
)


class ProductService:
    def __init__(self, db: Session):
        self.db = db
        self.products = ProductRepository(db)

    def list_public(self, *, query: str | None, limit: int, offset: int) -> ProductPage:
        items, total = self.products.list(
            public=True, query=query, limit=limit, offset=offset
        )
        return ProductPage(
            items=[ProductOut.model_validate(item) for item in items],
            total=total, limit=limit, offset=offset,
        )

    def list_admin(self, *, query: str | None, limit: int, offset: int) -> ProductAdminPage:
        items, total = self.products.list(
            public=False, query=query, limit=limit, offset=offset
        )
        return ProductAdminPage(
            items=[ProductAdminOut.model_validate(item) for item in items],
            total=total, limit=limit, offset=offset,
        )

    def get_public(self, product_id: uuid.UUID) -> ProductDetailOut:
        product = self.products.get(product_id, public=True)
        if product is None:
            raise AppException(404, "PRODUCT_NOT_FOUND", "Producto no encontrado.")
        related = [
            ProductOut.model_validate(item) for item in self.products.related(product)
        ]
        return ProductDetailOut.model_validate(product).model_copy(
            update={"related_products": related}
        )

    def get_admin(self, product_id: uuid.UUID) -> ProductAdminOut:
        product = self.products.get(product_id, public=False)
        if product is None:
            raise AppException(404, "PRODUCT_NOT_FOUND", "Producto no encontrado.")
        return ProductAdminOut.model_validate(product)

    def create(self, data: ProductCreate) -> ProductAdminOut:
        fields = data.model_dump(exclude={"images"})
        image_urls = [str(url) for url in data.images]
        try:
            product = self.products.create(fields, image_urls)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise AppException(
                500, "PRODUCT_WRITE_FAILED", "No fue posible guardar el producto."
            ) from None
        return self.get_admin(product.id)

    def patch(self, product_id: uuid.UUID, data: ProductPatch) -> ProductAdminOut:
        product = self.products.get(product_id, public=False)
        if product is None:
            raise AppException(404, "PRODUCT_NOT_FOUND", "Producto no encontrado.")
        fields = data.model_dump(exclude_unset=True, exclude={"images"})
        image_urls = (
            [str(url) for url in data.images]
            if "images" in data.model_fields_set and data.images is not None
            else None
        )
        try:
            self.products.update(product, fields, image_urls)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise AppException(
                500, "PRODUCT_WRITE_FAILED", "No fue posible guardar el producto."
            ) from None
        return self.get_admin(product_id)
