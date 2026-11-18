from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = BASE_DIR / ".env",
        env_file_encoding = "utf-8",
        extra = "ignore",
    )
    
    app_name: str = "La Tia Richard API"
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str | None = None
    test_database_url: str | None = None
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    
    cors_origins: list[str] = Field(
        default_factory = lambda: ["http://localhost:5173"]
    )
    cors_allow_credentials: bool = True
    session_cookie_name: str = "jardin_session"
    session_duration_hours: int = Field(default=8, ge=1, le=168)
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict"] = "lax"
    
    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list [str]) -> list[str]:
        if not origins or any (
            origin == "*"
            or origin.endswith("/")
            or not origin.startswith(("http://", "https://"))
            for  origin in origins
        ):
            raise ValueError(
                "CORS_ORGINS must be HTTP(S) explicit origins"
            )
        return origins
    
    @model_validator(mode = "after")
    def validate_production(self):
        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be false in production.")
            
            if any(
                not origin.startswith("https://")
                for origin in self.cors_origins
            ):
                raise ValueError(
                    "Production origins must use HTTPS."
                )
            if not self.session_cookie_secure:
                raise ValueError(
                    "SESSION_COOKIE_SECURE must be true in production."
                )
        return self
    
    
@lru_cache
def get_settings() -> Settings:
    return Settings()
