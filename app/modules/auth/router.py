from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_session,
    get_current_user,
    require_csrf,
    require_trusted_origin,
)
from app.modules.auth.models import UserSession
from app.modules.auth.schemas import (
    CSRFResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    service = AuthService(db)
    user = service.register(data)

    return RegisterResponse(
        user=user,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def login(
    data: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user, session_token, csrf_token = AuthService(db).login(data, settings)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        max_age=settings.session_duration_hours * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )
    return LoginResponse(user=user, csrf_token=csrf_token)


@router.get("/me", response_model=UserResponse)
def me(response: Response, user=Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user


@router.post(
    "/csrf",
    response_model=CSRFResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def csrf(
    response: Response,
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return CSRFResponse(csrf_token=AuthService(db).rotate_csrf(session))


@router.post(
    "/logout",
    response_model=LogoutResponse,
    dependencies=[Depends(require_trusted_origin)],
)
def logout(
    response: Response,
    session: UserSession = Depends(require_csrf),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    AuthService(db).logout(session)
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )
    return LogoutResponse()
