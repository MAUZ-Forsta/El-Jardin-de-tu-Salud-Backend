import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.core.config import get_settings


BASE_DIR = Path(__file__).resolve().parents[1]


def migrate_test_database():
    settings = get_settings()

    test_url = settings.test_database_url
    main_url = settings.database_url

    if not test_url or not main_url:
        raise RuntimeError(
            "DATABASE_URL y TEST_DATABASE_URL son obligatorias."
        )

    parsed_test = make_url(test_url)
    parsed_main = make_url(main_url)

    if parsed_test.database != "tia_richrad_test":
        raise RuntimeError(
            "La base de pruebas debe ser tia_richrad_test."
        )

    if parsed_test == parsed_main:
        raise RuntimeError(
            "La base de pruebas y la principal deben ser diferentes."
        )

    config = Config(str(BASE_DIR / "alembic.ini"))

    original_url = os.environ.get("DATABASE_URL")

    try:
        os.environ["DATABASE_URL"] = test_url
        get_settings.cache_clear()

        command.upgrade(config, "head")

        print("Migraciones aplicadas correctamente.")

    finally:
        if original_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_url

        get_settings.cache_clear()


if __name__ == "__main__":
    migrate_test_database()