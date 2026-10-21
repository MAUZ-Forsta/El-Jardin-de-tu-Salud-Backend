from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

def create_db_engine() -> Engine:
    settings = get_settings()
    
    if not settings.database_url:
        raise RuntimeError(
            "DATABSE_URL aren't config"
        )
        
    if not settings.database_url.startswith(
        "postgresql+psycopg://"
    ):
        raise ValueError(
            "DATABASE_URL must use psycopg controller"
        )
        
    return create_engine(
        settings.database_url,
        pool_pre_ping = True,
        pool_size = 5,
        max_overflow = 5,
        pool_timeout = 30,
        pool_recycle = 1800,
        echo = False,
    )
    
engine = create_db_engine()

SessionLocal = sessionmaker(
    bind = engine,
    autoflush = False,
    expire_on_commit = False,
)

def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session