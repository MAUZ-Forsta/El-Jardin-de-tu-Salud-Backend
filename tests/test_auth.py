import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import verify_password
from app.modules.users.models import ClientProfile, User


def registration_payload(email: str) -> dict:
    return {
        "email": email,
        "password": "password-seguro-123",
        "first_name": "Ana",
        "middle_name": "María",
        "last_name": "López",
        "second_last_name": "Pérez",
    }


def test_register_persists_client_and_profile(app_client, db_session):
    email = f"{db_session.info['created_prefix']}-register@example.com"
    response = app_client.post(
        "/api/v1/auth/register", json=registration_payload(email)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "CLIENT"
    assert "password" not in response.text
    assert "password_hash" not in response.text

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    assert user.role == "CLIENT"
    assert user.password_hash != "password-seguro-123"
    assert verify_password("password-seguro-123", user.password_hash)
    assert db_session.scalar(
        select(ClientProfile).where(ClientProfile.user_id == user.id)
    ) is not None


def test_register_rejects_duplicate_email(app_client, db_session):
    email = f"{db_session.info['created_prefix']}-duplicate@example.com"
    payload = registration_payload(email)
    assert app_client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = app_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "password" not in response.text


@pytest.mark.parametrize(
    "change",
    [
        {"first_name": ""},
        {"first_name": "   "},
        {"last_name": ""},
        {"email": "not-an-email"},
    ],
)
def test_register_rejects_invalid_required_data(app_client, db_session, change):
    email = f"{db_session.info['created_prefix']}-invalid@example.com"
    payload = registration_payload(email)
    payload.update(change)
    response = app_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_register_rejects_extra_fields_and_role_injection(app_client, db_session):
    email = f"{db_session.info['created_prefix']}-extra@example.com"
    payload = registration_payload(email)
    payload["role"] = "ADMIN"
    response = app_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_register_rejects_missing_required_fields(app_client, db_session):
    email = f"{db_session.info['created_prefix']}-missing@example.com"
    payload = registration_payload(email)
    del payload["last_name"]
    response = app_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_register_rolls_back_on_integrity_error(app_client, db_session, monkeypatch):
    email = f"{db_session.info['created_prefix']}-rollback@example.com"
    original_commit = db_session.commit

    def failing_commit():
        raise IntegrityError("forced test failure", {}, None)

    monkeypatch.setattr(db_session, "commit", failing_commit)
    response = app_client.post(
        "/api/v1/auth/register", json=registration_payload(email)
    )
    monkeypatch.setattr(db_session, "commit", original_commit)

    assert response.status_code == 409
    assert db_session.scalar(select(User).where(User.email == email)) is None
