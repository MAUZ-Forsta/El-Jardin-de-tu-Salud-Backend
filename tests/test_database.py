import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings


BASE_DIR = Path(__file__).resolve().parents[1]


def migrate_test_database():
    settings = get_settings()

    if not settings.test_database_url:
        raise RuntimeError(
            "TEST_DATABASE_URL no está configurada."
        )

    test_url = make_url(settings.test_database_url)

    if test_url.database != "tia_richrad_test":
        raise RuntimeError(
            "La base de datos de pruebas no es la esperada."
        )

    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL no está configurada."
        )

    main_url = make_url(settings.database_url)

    if main_url == test_url:
        raise RuntimeError(
            "La base de pruebas no puede ser la base principal."
        )

    config = Config(str(BASE_DIR / "alembic.ini"))

    original_url = os.environ.get("DATABASE_URL")

    try:
        # Sobrescribe la conexión solamente durante la migración.
        os.environ["DATABASE_URL"] = settings.test_database_url

        # env.py utiliza get_settings(), que tiene caché.
        get_settings.cache_clear()

        command.upgrade(config, "head")

    finally:
        if original_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_url

        get_settings.cache_clear()

    engine = create_engine(settings.test_database_url)

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("Migraciones aplicadas a tia_richrad_test.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    migrate_test_database()