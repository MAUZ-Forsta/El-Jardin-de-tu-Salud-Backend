import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import create_app
from app.modules.auth.models import UserSession
from app.modules.products.models import Product
from app.modules.users.models import ClientProfile, User


@pytest.fixture
def test_engine() -> Generator[Engine, None, None]:
    settings = get_settings()
    if not settings.test_database_url:
        pytest.skip("TEST_DATABASE_URL no está configurada")
    url = make_url(settings.test_database_url)
    if url.database != "tia_richrad_test":
        pytest.fail("Las pruebas solo pueden usar tia_richrad_test")
    if settings.database_url and make_url(settings.database_url) == url:
        pytest.fail("La base de pruebas no puede ser la base principal")
    engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    db = Session(test_engine)
    prefix = f"codex-test-{uuid.uuid4()}"
    db.info["created_prefix"] = prefix
    try:
        yield db
    finally:
        db.rollback()
        products = db.scalars(
            select(Product).where(Product.name.like(f"{prefix}-%"))
        ).all()
        for product in products:
            db.delete(product)
        if products:
            db.commit()
        users = db.scalars(
            select(User).where(User.email.like(f"{prefix}-%@example.com"))
        ).all()
        user_ids = [user.id for user in users]
        if user_ids:
            db.execute(delete(UserSession).where(UserSession.user_id.in_(user_ids)))
            db.execute(delete(ClientProfile).where(ClientProfile.user_id.in_(user_ids)))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.commit()
        db.close()


@pytest.fixture
def app_client(db_session: Session) -> Generator[TestClient, None, None]:
    test_url = get_settings().test_database_url
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url=test_url,
        test_database_url=test_url,
        cors_origins=["http://localhost:5173"],
        cors_allow_credentials=True,
    )
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client


@pytest.fixture
def make_user(db_session: Session):
    def factory(
        *,
        active: bool = True,
        email: str | None = None,
        password: str = "password-seguro-123",
    ) -> User:
        prefix = db_session.info["created_prefix"]
        user = User(
            email=email or f"{prefix}-{uuid.uuid4()}@example.com",
            password_hash=hash_password(password),
            is_active=active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return factory
