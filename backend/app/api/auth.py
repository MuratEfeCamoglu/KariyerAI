from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import ACCESS_TOKEN_TTL, AUTH_COOKIE_NAME, create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, db: DbSession) -> UserOut:
    client_key = request.client.host if request.client else "unknown"
    user = auth_service.authenticate(
        db, email=body.email, password=body.password, client_key=client_key
    )
    _set_session_cookie(response, user.id)
    return UserOut.model_validate(user)


@router.post("/register", status_code=201)
def register(body: RegisterRequest, request: Request, response: Response, db: DbSession) -> UserOut:
    client_key = request.client.host if request.client else "unknown"
    user = auth_service.register(
        db,
        email=body.email,
        full_name=body.full_name,
        password=body.password,
        client_key=client_key,
    )
    _set_session_cookie(response, user.id)
    return UserOut.model_validate(user)


def _set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        AUTH_COOKIE_NAME,
        create_access_token(user_id),
        max_age=int(ACCESS_TOKEN_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
        path="/",
    )


@router.post("/logout", status_code=204)
def logout(_user: CurrentUser, response: Response) -> None:
    response.delete_cookie(
        AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
    )


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
