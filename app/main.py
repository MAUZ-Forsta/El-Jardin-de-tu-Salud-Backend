from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers

def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    
    app = FastAPI(
        title = settings.app_name,
        debug = settings.debug,
        docs_url = "/docs" if settings.app_env != "production" else None,
        redoc_url = "/redoc" if settings.app_env != "production" else None,
        openapi_url = (
            "/openapi.json"
            if settings.app_env != "production"
            else None
        )
    )
    
    register_exception_handlers(app)
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    return CORSMiddleware(
        app = app,
        allow_origins = settings.cors_origins,
        allow_credentials = settings.cors_allow_credentials,
        allow_methods = [
            "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
        ],
        allow_headers = ["Authorization", "Content-Type"],
    )
    
app = create_app