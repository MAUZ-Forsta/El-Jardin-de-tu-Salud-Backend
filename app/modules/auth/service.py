from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.core.security import hash_password
from app.modules.auth.schemas import RegisterRequest
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

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
