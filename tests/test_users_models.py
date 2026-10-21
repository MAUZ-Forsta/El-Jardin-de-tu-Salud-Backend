import uuid

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.users.models import ClientProfile, User


@pytest.fixture
def test_engine():
    settings = get_settings()
    url = settings.test_database_url

    if not url:
        pytest.fail("TEST_DATABASE_URL no configurada")

    parsed_url = make_url(url)

    if parsed_url.database != "tia_richrad_test":
        pytest.fail(
            "La conexión no apunta a tia_richrad_test"
        )

    engine = create_engine(
        url,
        pool_pre_ping=True,
    )

    try:
        yield engine
    finally:
        engine.dispose()


def test_tables_exist(test_engine):
    inspector = inspect(test_engine)

    assert inspector.has_table("users")
    assert inspector.has_table("client_profiles")


def test_user_profile_relationship(test_engine):
    with Session(test_engine) as session:
        user = User(
            email=f"{uuid.uuid4()}@example.com",
            password_hash="hash-ficticio-no-autenticable",
        )

        user.profile = ClientProfile(
            first_name="Cliente",
            last_name="Prueba",
        )

        session.add(user)
        session.flush()

        assert user.profile.user_id == user.id

        session.rollback()


def test_email_is_case_insensitive_unique(test_engine):
    email = f"{uuid.uuid4()}@example.com"

    with Session(test_engine) as session:
        first = User(
            email=email,
            password_hash="hash-ficticio-no-autenticable",
        )

        session.add(first)
        session.flush()

        duplicate = User(
            email=email.upper(),
            password_hash="hash-ficticio-no-autenticable",
        )

        session.add(duplicate)

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()


def test_invalid_role_is_rejected(test_engine):
    with Session(test_engine) as session:
        user = User(
            email=f"{uuid.uuid4()}@example.com",
            password_hash="hash-ficticio-no-autenticable",
            role="SUPERUSER",
        )

        session.add(user)

        with pytest.raises(IntegrityError):
            session.flush()

        session.rollback()