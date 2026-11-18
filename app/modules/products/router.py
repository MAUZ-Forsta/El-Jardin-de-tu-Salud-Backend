import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import require_admin, require_admin_write
from app.modules.products.schemas import (
    ProductAdminOut,
    ProductAdminPage,
    ProductCreate,
    ProductDetailOut,
    ProductPage,
    ProductPatch,
)
from app.modules.products.service import ProductService

public_router = APIRouter(prefix="/api/v1/products", tags=["Products"])
admin_router = APIRouter(prefix="/api/v1/admin/products", tags=["Product administration"])


@public_router.get("", response_model=ProductPage)
def list_products(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return ProductService(db).list_public(
        query=q.strip() or None if q is not None else None,
        limit=limit, offset=offset,
    )


@public_router.get("/{product_id}", response_model=ProductDetailOut)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    return ProductService(db).get_public(product_id)


@admin_router.get("", response_model=ProductAdminPage, dependencies=[Depends(require_admin)])
def list_admin_products(
    q: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return ProductService(db).list_admin(
        query=q.strip() or None if q is not None else None,
        limit=limit, offset=offset,
    )


@admin_router.get(
    "/{product_id}", response_model=ProductAdminOut, dependencies=[Depends(require_admin)]
)
def get_admin_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    return ProductService(db).get_admin(product_id)


@admin_router.post(
    "", response_model=ProductAdminOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_write)],
)
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    return ProductService(db).create(data)


@admin_router.patch(
    "/{product_id}", response_model=ProductAdminOut,
    dependencies=[Depends(require_admin_write)],
)
def patch_product(
    product_id: uuid.UUID, data: ProductPatch, db: Session = Depends(get_db)
):
    return ProductService(db).patch(product_id, data)
