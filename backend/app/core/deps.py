from typing import Annotated

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security import AUTH_COOKIE_NAME, decode_access_token
from app.models.user import User, UserRole

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    access_token: Annotated[str | None, Cookie(alias=AUTH_COOKIE_NAME)] = None,
) -> User:
    user_id = decode_access_token(access_token) if access_token else None
    user = db.get(User, user_id) if user_id is not None else None
    # Pasifleştirilen kullanıcının elindeki token da hemen geçersiz olmalı (F2).
    # Onaylanmamış hesabın normalde token'ı olmaz; bu ikinci savunma hattıdır.
    if user is None or not user.is_active or not user.is_approved:
        raise AuthenticationError("Oturum açmanız gerekiyor")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise PermissionDeniedError("Bu işlem için yetkiniz yok")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_recruiter(user: CurrentUser) -> User:
    """İşveren uçları yalnızca İK uzmanınındır; admin ve iş arayan 403 alır (yalıtım)."""
    if user.role != UserRole.RECRUITER:
        raise PermissionDeniedError("Bu işlem için yetkiniz yok")
    return user


RecruiterUser = Annotated[User, Depends(require_recruiter)]


def require_seeker(user: CurrentUser) -> User:
    if user.role != UserRole.SEEKER:
        raise PermissionDeniedError("Bu işlem için yetkiniz yok")
    return user


SeekerUser = Annotated[User, Depends(require_seeker)]
