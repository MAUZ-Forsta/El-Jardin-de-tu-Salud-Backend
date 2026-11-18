import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.models import UserSession


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: uuid.UUID,
        session_token_hash: str,
        csrf_token_hash: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> UserSession:
        session = UserSession(
            user_id=user_id,
            session_token_hash=session_token_hash,
            csrf_token_hash=csrf_token_hash,
            created_at=created_at,
            expires_at=expires_at,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        return self.db.scalar(
            select(UserSession).where(UserSession.session_token_hash == token_hash)
        )

    def revoke(self, session: UserSession, revoked_at: datetime) -> None:
        session.revoked_at = revoked_at
        self.db.flush()

    def update_csrf_hash(self, session: UserSession, csrf_token_hash: str) -> None:
        session.csrf_token_hash = csrf_token_hash
        self.db.flush()
