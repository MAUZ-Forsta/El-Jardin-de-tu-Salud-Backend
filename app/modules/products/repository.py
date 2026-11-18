import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.products.models import Product, ProductImage


def _search_condition(query: str):
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    return or_(
        Product.name.ilike(pattern, escape="\\"),
        Product.description.ilike(pattern, escape="\\"),
        Product.category.ilike(pattern, escape="\\"),
        Product.ingredients.ilike(pattern, escape="\\"),
        Product.benefits.ilike(pattern, escape="\\"),
        Product.properties.ilike(pattern, escape="\\"),
        Product.suggested_use.ilike(pattern, escape="\\"),
        Product.warnings.ilike(pattern, escape="\\"),
    )


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self, *, public: bool, query: str | None, limit: int, offset: int
    ) -> tuple[Sequence[Product], int]:
        conditions = [Product.kind == "PHYSICAL"]
        if public:
            conditions.append(Product.is_active.is_(True))
        if query:
            conditions.append(_search_condition(query))
        total = self.db.scalar(select(func.count(Product.id)).where(*conditions)) or 0
        statement = (
            select(Product)
            .where(*conditions)
            .options(selectinload(Product.images))
            .order_by(Product.created_at.desc(), Product.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return self.db.scalars(statement).all(), total

    def get(self, product_id: uuid.UUID, *, public: bool) -> Product | None:
        statement = select(Product).where(
            Product.id == product_id, Product.kind == "PHYSICAL"
        ).options(selectinload(Product.images))
        if public:
            statement = statement.where(Product.is_active.is_(True))
        return self.db.scalar(statement)

    def related(self, product: Product, limit: int = 4) -> Sequence[Product]:
        statement = (
            select(Product)
            .where(
                Product.kind == "PHYSICAL",
                Product.is_active.is_(True),
                Product.category == product.category,
                Product.id != product.id,
            )
            .options(selectinload(Product.images))
            .order_by(Product.created_at.desc(), Product.id.desc())
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def create(self, fields: dict, image_urls: list[str]) -> Product:
        product = Product(kind="PHYSICAL", is_active=False, **fields)
        product.images = [
            ProductImage(url=url, position=position)
            for position, url in enumerate(image_urls)
        ]
        self.db.add(product)
        self.db.flush()
        return product

    def update(self, product: Product, fields: dict, image_urls: list[str] | None) -> None:
        for name, value in fields.items():
            setattr(product, name, value)
        if image_urls is not None:
            for position, url in enumerate(image_urls):
                if position < len(product.images):
                    product.images[position].url = url
                else:
                    product.images.append(ProductImage(url=url, position=position))
            del product.images[len(image_urls):]
        self.db.flush()
