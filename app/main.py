from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.modules.auth.router import router as auth_router
from app.modules.products.router import admin_router as products_admin_router
from app.modules.products.router import public_router as products_public_router


def create_app(settings: Settings | None = None) -> FastAPI:
    supplied_settings = settings is not None
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
    if supplied_settings:
        app.dependency_overrides[get_settings] = lambda: settings
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    app.include_router(auth_router)
    app.include_router(products_public_router)
    app.include_router(products_admin_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins = settings.cors_origins,
        allow_credentials = settings.cors_allow_credentials,
        allow_methods = [
            "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
        ],
        allow_headers = ["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    return app


app = create_app
