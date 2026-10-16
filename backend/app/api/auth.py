from fastapi import APIRouter, Request, Response

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.security import ACCESS_TOKEN_TTL, AUTH_COOKIE_NAME, create_access_token
from app.schemas.auth import LoginRequest
from app.schemas.user import UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, db: DbSession) -> UserOut:
    client_key = request.client.host if request.client else "unknown"
    user = auth_service.authenticate(
        db, email=body.email, password=body.password, client_key=client_key
    )
    response.set_cookie(
        AUTH_COOKIE_NAME,
        create_access_token(user.id),
        max_age=int(ACCESS_TOKEN_TTL.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
        path="/",
    )
    return UserOut.model_validate(user)


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
