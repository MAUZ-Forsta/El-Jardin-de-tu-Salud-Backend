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
    debug: bool = False
    
    cors_origins: list[str] = Field(
        default_factory = lambda: ["http://localhost:5173"]
    )
    cors_allow_credentials: bool = False
    
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
        return self
    
    
@lru_cache
def get_settings() -> Settings:
    return Settings()