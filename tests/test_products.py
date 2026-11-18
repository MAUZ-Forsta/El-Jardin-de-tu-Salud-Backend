import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.products.models import Product, ProductImage

ORIGIN = "http://localhost:5173"
PUBLIC = "/api/v1/products"
ADMIN = "/api/v1/admin/products"


def product_payload(prefix: str, suffix: str = "manzanilla") -> dict:
    return {
        "name": f"{prefix}-{suffix}",
        "description": "Infusión de planta medicinal.",
        "category": "MEDICINAL_PLANT",
        "price": "12.99",
        "images": [
            "https://example.test/manzanilla-principal.jpg",
            "https://example.test/manzanilla-detalle.jpg",
        ],
        "ingredients": "Manzanilla",
        "benefits": "Información general sobre la planta.",
        "suggested_use": "Preparar una infusión.",
        "warnings": "Consultar a un profesional si corresponde.",
    }


@pytest.fixture
def admin_headers(app_client, make_user, db_session):
    user = make_user()
    user.role = "ADMIN"
    db_session.commit()
    response = app_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "password-seguro-123"},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


def create_product(app_client, admin_headers, prefix, suffix="manzanilla"):
    response = app_client.post(
        ADMIN, json=product_payload(prefix, suffix), headers=admin_headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def publish(app_client, admin_headers, product_id):
    response = app_client.patch(
        f"{ADMIN}/{product_id}", json={"is_active": True}, headers=admin_headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_create_persists_images_and_starts_inactive(
    app_client, admin_headers, db_session
):
    prefix = db_session.info["created_prefix"]
    created = create_product(app_client, admin_headers, prefix)
    product_id = uuid.UUID(created["id"])

    assert created["is_active"] is False
    assert created["price"] == "12.99"
    assert created["stock_available"] is None
    assert created["main_image_url"].endswith("principal.jpg")
    assert [item["position"] for item in created["images"]] == [0, 1]
    assert app_client.get(f"{PUBLIC}/{product_id}").status_code == 404

    persisted = db_session.get(Product, product_id)
    assert persisted is not None
    assert persisted.price == Decimal("12.99")
    assert len(db_session.scalars(
        select(ProductImage).where(ProductImage.product_id == product_id)
    ).all()) == 2


def test_public_search_pagination_and_detail(app_client, admin_headers, db_session):
    prefix = db_session.info["created_prefix"]
    ids = []
    for suffix in ("manzanilla", "lavanda", "menta"):
        created = create_product(app_client, admin_headers, prefix, suffix)
        ids.append(created["id"])
        publish(app_client, admin_headers, created["id"])

    page = app_client.get(PUBLIC, params={"q": prefix, "limit": 2, "offset": 1})
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 2
    assert page.json()["limit"] == 2
    assert page.json()["offset"] == 1
    assert all("is_active" not in item for item in page.json()["items"])

    match = app_client.get(PUBLIC, params={"q": f"{prefix}-MANZ"})
    assert match.status_code == 200
    assert match.json()["total"] == 1

    detail = app_client.get(f"{PUBLIC}/{ids[0]}")
    assert detail.status_code == 200
    assert detail.json()["ingredients"] == "Manzanilla"
    assert len(detail.json()["related_products"]) == 2
    assert all(item["id"] != ids[0] for item in detail.json()["related_products"])


def test_search_treats_wildcards_as_literal(app_client, admin_headers, db_session):
    prefix = db_session.info["created_prefix"]
    created = create_product(app_client, admin_headers, prefix, "té_%")
    publish(app_client, admin_headers, created["id"])

    response = app_client.get(PUBLIC, params={"q": f"{prefix}-té_%"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == created["id"]


def test_inactive_hidden_and_admin_can_reactivate(app_client, admin_headers, db_session):
    prefix = db_session.info["created_prefix"]
    created = create_product(app_client, admin_headers, prefix)
    product_id = created["id"]
    assert app_client.get(PUBLIC, params={"q": prefix}).json()["total"] == 0
    assert app_client.get(ADMIN, params={"q": prefix}).json()["total"] == 1
    assert app_client.get(f"{ADMIN}/{product_id}").status_code == 200

    publish(app_client, admin_headers, product_id)
    assert app_client.get(f"{PUBLIC}/{product_id}").status_code == 200

    disabled = app_client.patch(
        f"{ADMIN}/{product_id}", json={"is_active": False}, headers=admin_headers
    )
    assert disabled.status_code == 200
    assert app_client.get(f"{PUBLIC}/{product_id}").status_code == 404
    assert app_client.get(f"{ADMIN}/{product_id}").status_code == 200
    assert app_client.delete(f"{ADMIN}/{product_id}", headers=admin_headers).status_code == 405


def test_patch_content_and_gallery(app_client, admin_headers, db_session):
    prefix = db_session.info["created_prefix"]
    created = create_product(app_client, admin_headers, prefix)
    response = app_client.patch(
        f"{ADMIN}/{created['id']}",
        json={"price": "14.50", "images": ["https://example.test/nueva.jpg"]},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["price"] == "14.50"
    assert len(response.json()["images"]) == 1
    assert response.json()["main_image_url"].endswith("nueva.jpg")
    assert db_session.scalar(
        select(ProductImage).where(ProductImage.product_id == uuid.UUID(created["id"]))
        .order_by(ProductImage.position)
    ).url.endswith("nueva.jpg")


@pytest.mark.parametrize(
    "change",
    [
        {"price": "-0.01"},
        {"price": "NaN"},
        {"category": "COURSE"},
        {"images": []},
        {"images": ["javascript:alert(1)"]},
        {"name": "   "},
        {"is_active": True},
        {"stock": 10},
        {"kind": "COURSE"},
    ],
)
def test_create_rejects_invalid_or_unauthorized_fields(
    app_client, admin_headers, db_session, change
):
    payload = product_payload(db_session.info["created_prefix"])
    payload.update(change)
    response = app_client.post(ADMIN, json=payload, headers=admin_headers)
    assert response.status_code == 422


@pytest.mark.parametrize("change", [{}, {"name": None}, {"price": None}, {"price": "-1"}, {"stock": 2}])
def test_patch_rejects_invalid_fields(app_client, admin_headers, db_session, change):
    created = create_product(app_client, admin_headers, db_session.info["created_prefix"])
    response = app_client.patch(
        f"{ADMIN}/{created['id']}", json=change, headers=admin_headers
    )
    assert response.status_code == 422


def test_not_found_and_invalid_identifier(app_client, admin_headers):
    missing = uuid.uuid4()
    assert app_client.get(f"{PUBLIC}/{missing}").status_code == 404
    assert app_client.get(f"{ADMIN}/{missing}").status_code == 404
    assert app_client.patch(
        f"{ADMIN}/{missing}", json={"is_active": True}, headers=admin_headers
    ).status_code == 404
    assert app_client.get(f"{PUBLIC}/not-a-uuid").status_code == 422


def test_admin_routes_require_session_role_origin_and_csrf(app_client, make_user, db_session):
    assert app_client.get(ADMIN).status_code == 401
    assert app_client.post(
        ADMIN, json=product_payload(db_session.info["created_prefix"]),
        headers={"Origin": ORIGIN},
    ).status_code == 401

    user = make_user()
    login = app_client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "password-seguro-123"},
        headers={"Origin": ORIGIN},
    )
    assert login.status_code == 200
    headers = {"Origin": ORIGIN, "X-CSRF-Token": login.json()["csrf_token"]}
    assert app_client.get(ADMIN).status_code == 403
    assert app_client.post(
        ADMIN, json=product_payload(db_session.info["created_prefix"]),
        headers=headers,
    ).status_code == 403


def test_admin_write_rejects_missing_origin_or_csrf(
    app_client, admin_headers, db_session
):
    payload = product_payload(db_session.info["created_prefix"])
    assert app_client.post(
        ADMIN, json=payload, headers={"X-CSRF-Token": admin_headers["X-CSRF-Token"]}
    ).status_code == 403
    assert app_client.post(
        ADMIN, json=payload, headers={"Origin": ORIGIN}
    ).status_code == 403


def test_database_constraints_reject_negative_price_and_duplicate_image_position(
    test_engine
):
    with Session(test_engine) as session:
        product = Product(
            kind="PHYSICAL", category="MEDICINAL_PLANT", name="constraint-test",
            description="Prueba", price=Decimal("-1"),
        )
        product.images = [ProductImage(url="https://example.test/a.jpg", position=0)]
        session.add(product)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    with Session(test_engine) as session:
        product = Product(
            kind="PHYSICAL", category="MEDICINAL_PLANT", name="constraint-test",
            description="Prueba", price=Decimal("1"),
        )
        product.images = [
            ProductImage(url="https://example.test/a.jpg", position=0),
            ProductImage(url="https://example.test/b.jpg", position=0),
        ]
        session.add(product)
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_create_rolls_back_on_persistence_error(
    app_client, admin_headers, db_session, monkeypatch
):
    prefix = db_session.info["created_prefix"]
    original_commit = db_session.commit

    def failing_commit():
        raise SQLAlchemyError("fallo de prueba")

    monkeypatch.setattr(db_session, "commit", failing_commit)
    response = app_client.post(
        ADMIN, json=product_payload(prefix), headers=admin_headers
    )
    monkeypatch.setattr(db_session, "commit", original_commit)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "PRODUCT_WRITE_FAILED"
    assert db_session.scalar(select(Product).where(Product.name.like(f"{prefix}-%"))) is None
