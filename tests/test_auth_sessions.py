from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import hash_token
from app.modules.auth.models import UserSession

ORIGIN = "http://localhost:5173"


def login(client, user, password="password-seguro-123", origin=ORIGIN):
    return client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
        headers={"Origin": origin},
    )


def csrf_headers(token):
    return {"Origin": ORIGIN, "X-CSRF-Token": token}


def test_login_creates_persistent_session_and_cookie(app_client, db_session, make_user):
    user = make_user()
    response = login(app_client, user)
    assert response.status_code == 200
    assert response.json()["user"]["email"] == user.email
    assert response.json()["csrf_token"]
    assert "password_hash" not in response.text

    cookie_header = response.headers["set-cookie"]
    assert "jardin_session=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header
    assert "Path=/" in cookie_header
    assert "Max-Age=28800" in cookie_header
    assert "Secure" not in cookie_header

    raw_session_token = app_client.cookies.get("jardin_session")
    session = db_session.scalar(
        select(UserSession).where(UserSession.user_id == user.id)
    )
    assert session is not None
    assert session.session_token_hash == hash_token(raw_session_token)
    assert session.session_token_hash != raw_session_token
    assert session.csrf_token_hash == hash_token(response.json()["csrf_token"])


def test_login_rejects_invalid_credentials_generically(app_client, make_user):
    user = make_user()
    wrong = login(app_client, user, password="contraseña-equivocada")
    missing = app_client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "contraseña-equivocada"},
        headers={"Origin": ORIGIN},
    )
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


def test_login_rejects_inactive_user_and_untrusted_origin(app_client, make_user):
    inactive = make_user(active=False)
    assert login(app_client, inactive).status_code == 401
    active = make_user()
    assert login(app_client, active, origin="https://untrusted.example").status_code == 403


def test_login_rejects_invalid_payload(app_client):
    response = app_client.post(
        "/api/v1/auth/login",
        json={"email": "invalid", "password": ""},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 422


def test_me_returns_public_user_and_requires_session(app_client, make_user):
    user = make_user()
    assert app_client.get("/api/v1/auth/me").status_code == 401
    login(app_client, user)
    response = app_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["email"] == user.email
    assert "password_hash" not in response.text
    assert "session_token" not in response.text


def test_me_rejects_an_invalid_session_cookie(app_client):
    app_client.cookies.set("jardin_session", "invalid-session-token")
    assert app_client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_invalid_expired_revoked_and_inactive_sessions(
    app_client, db_session, make_user
):
    user = make_user()
    login(app_client, user)
    session = db_session.scalar(select(UserSession).where(UserSession.user_id == user.id))

    session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()
    assert app_client.get("/api/v1/auth/me").status_code == 401

    session.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    session.revoked_at = datetime.now(timezone.utc)
    db_session.commit()
    assert app_client.get("/api/v1/auth/me").status_code == 401

    session.revoked_at = None
    user.is_active = False
    db_session.commit()
    assert app_client.get("/api/v1/auth/me").status_code == 401


def test_csrf_rotation_invalidates_old_token_and_requires_origin(
    app_client, db_session, make_user
):
    user = make_user()
    old_token = login(app_client, user).json()["csrf_token"]
    rotated = app_client.post("/api/v1/auth/csrf", headers={"Origin": ORIGIN})
    assert rotated.status_code == 200
    new_token = rotated.json()["csrf_token"]
    assert new_token != old_token

    session = db_session.scalar(select(UserSession).where(UserSession.user_id == user.id))
    assert session.csrf_token_hash == hash_token(new_token)
    assert session.csrf_token_hash != old_token
    assert app_client.post(
        "/api/v1/auth/logout", headers=csrf_headers(old_token)
    ).status_code == 403
    assert app_client.post(
        "/api/v1/auth/logout", headers=csrf_headers(new_token)
    ).status_code == 200

    login(app_client, user)
    assert app_client.post(
        "/api/v1/auth/csrf", headers={"Origin": "https://untrusted.example"}
    ).status_code == 403


def test_csrf_token_belongs_to_the_current_session(app_client, make_user):
    first_user = make_user()
    first_token = login(app_client, first_user).json()["csrf_token"]
    second_user = make_user()
    login(app_client, second_user)
    assert app_client.post(
        "/api/v1/auth/logout", headers=csrf_headers(first_token)
    ).status_code == 403


def test_logout_revokes_session_deletes_cookie_and_prevents_reuse(
    app_client, db_session, make_user
):
    user = make_user()
    login(app_client, user)
    old_cookie = app_client.cookies.get("jardin_session")
    csrf_token = app_client.post("/api/v1/auth/csrf", headers={"Origin": ORIGIN}).json()[
        "csrf_token"
    ]
    response = app_client.post("/api/v1/auth/logout", headers=csrf_headers(csrf_token))
    assert response.status_code == 200
    assert "Max-Age=0" in response.headers["set-cookie"]

    session = db_session.scalar(select(UserSession).where(UserSession.user_id == user.id))
    assert session.revoked_at is not None
    app_client.cookies.set("jardin_session", old_cookie)
    assert app_client.get("/api/v1/auth/me").status_code == 401


def test_logout_requires_csrf_and_trusted_origin(app_client, make_user):
    user = make_user()
    login(app_client, user)
    assert app_client.post(
        "/api/v1/auth/logout", headers={"Origin": ORIGIN}
    ).status_code == 403
    assert app_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://untrusted.example", "X-CSRF-Token": "wrong"},
    ).status_code == 403


def test_logout_database_error_does_not_confirm_logout(
    app_client, db_session, make_user, monkeypatch
):
    user = make_user()
    login(app_client, user)
    csrf_token = app_client.post("/api/v1/auth/csrf", headers={"Origin": ORIGIN}).json()[
        "csrf_token"
    ]
    original_commit = db_session.commit

    def failing_commit():
        raise SQLAlchemyError("forced test failure")

    monkeypatch.setattr(db_session, "commit", failing_commit)
    response = app_client.post("/api/v1/auth/logout", headers=csrf_headers(csrf_token))
    monkeypatch.setattr(db_session, "commit", original_commit)

    assert response.status_code == 500
    db_session.expire_all()
    session = db_session.scalar(select(UserSession).where(UserSession.user_id == user.id))
    assert session.revoked_at is None
