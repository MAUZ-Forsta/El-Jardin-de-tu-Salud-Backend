from datetime import datetime, timezone

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import AppException
from app.core.security import hash_token, tokens_match
from app.db.session import get_db
from app.modules.auth.models import UserSession
from app.modules.auth.repository import SessionRepository
from app.modules.users.models import User


def require_trusted_origin(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    origin = request.headers.get("origin")
    if not origin or origin not in settings.cors_origins:
        raise AppException(403, "UNTRUSTED_ORIGIN", "Origen no autorizado.")


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserSession:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise AppException(401, "AUTHENTICATION_REQUIRED", "Autenticación requerida.")
    session = SessionRepository(db).get_by_token_hash(hash_token(token))
    now = datetime.now(timezone.utc)
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise AppException(401, "INVALID_SESSION", "La sesión no es válida.")
    if session.user is None or not session.user.is_active:
        raise AppException(401, "INVALID_SESSION", "La sesión no es válida.")
    return session


def get_current_user(
    session: UserSession = Depends(get_current_session),
) -> User:
    return session.user


def require_csrf(
    session: UserSession = Depends(get_current_session),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> UserSession:
    if not csrf_token or not tokens_match(csrf_token, session.csrf_token_hash):
        raise AppException(403, "INVALID_CSRF_TOKEN", "Token CSRF inválido.")
    return session
