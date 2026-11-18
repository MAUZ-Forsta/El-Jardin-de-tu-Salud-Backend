from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.users.models import ClientProfile, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(
            func.lower(User.email) == email.strip().lower()
        )

        return self.db.scalar(stmt)

    def create_client(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        middle_name: str | None = None,
        second_last_name: str | None = None,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            role="CLIENT",
            is_active=True,
        )

        user.profile = ClientProfile(
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            second_last_name=second_last_name,
        )

        self.db.add(user)
        self.db.flush()

        return user