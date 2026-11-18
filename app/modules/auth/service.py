from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import AppException
from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.modules.auth.models import UserSession
from app.modules.auth.repository import SessionRepository
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)

    def register(self, data: RegisterRequest) -> User:
        email = str(data.email).strip().lower()

        if self.users.get_by_email(email):
            raise AppException(
                status_code=409,
                code="EMAIL_ALREADY_EXISTS",
                message="El correo electrónico ya está registrado.",
            )

        try:
            user = self.users.create_client(
                email=email,
                password_hash=hash_password(data.password),
                first_name=data.first_name,
                middle_name=data.middle_name,
                last_name=data.last_name,
                second_last_name=data.second_last_name,
            )

            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError:
            self.db.rollback()
            raise AppException(
                status_code=409,
                code="REGISTRATION_CONFLICT",
                message="No fue posible completar el registro.",
            ) from None

    def login(self, data: LoginRequest, settings: Settings) -> tuple[User, str, str]:
        user = self.users.get_by_email(str(data.email))
        valid = user is not None and verify_password(data.password, user.password_hash)
        if not valid or not user.is_active:
            raise AppException(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Credenciales incorrectas.",
            )

        session_token = generate_token()
        csrf_token = generate_token()
        now = datetime.now(timezone.utc)
        try:
            self.sessions.create(
                user_id=user.id,
                session_token_hash=hash_token(session_token),
                csrf_token_hash=hash_token(csrf_token),
                created_at=now,
                expires_at=now + timedelta(hours=settings.session_duration_hours),
            )
            self.db.commit()
            self.db.refresh(user)
        except SQLAlchemyError:
            self.db.rollback()
            raise AppException(
                status_code=500,
                code="SESSION_CREATION_FAILED",
                message="No fue posible iniciar la sesión.",
            ) from None
        return user, session_token, csrf_token

    def rotate_csrf(self, session: UserSession) -> str:
        csrf_token = generate_token()
        try:
            self.sessions.update_csrf_hash(session, hash_token(csrf_token))
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise AppException(
                status_code=500,
                code="CSRF_ROTATION_FAILED",
                message="No fue posible renovar el token CSRF.",
            ) from None
        return csrf_token

    def logout(self, session: UserSession) -> None:
        try:
            self.sessions.revoke(session, datetime.now(timezone.utc))
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            raise AppException(
                status_code=500,
                code="LOGOUT_FAILED",
                message="No fue posible cerrar la sesión.",
            ) from None
