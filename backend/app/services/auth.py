from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, PermissionDeniedError, TooManyRequestsError
from app.core.security import (
    login_rate_limiter,
    register_rate_limiter,
    verify_password_or_dummy,
)
from app.models.user import User, UserRole
from app.services import audit, users

INVALID_CREDENTIALS = "E-posta veya şifre hatalı"
PENDING_APPROVAL = "Hesabınız yönetici onayı bekliyor"


def authenticate(db: Session, *, email: str, password: str, client_key: str) -> User:
    if login_rate_limiter.is_blocked(client_key):
        raise TooManyRequestsError(
            "Çok fazla başarısız giriş denemesi. Lütfen bir dakika sonra tekrar deneyin."
        )

    user = db.scalar(select(User).where(User.email == email.lower()))
    password_ok = verify_password_or_dummy(password, user.password_hash if user else None)
    # Pasif kullanıcıya da aynı genel mesaj: hangi hesapların var olduğu sızmasın.
    if user is None or not password_ok or not user.is_active:
        login_rate_limiter.record_failure(client_key)
        raise AuthenticationError(INVALID_CREDENTIALS)
    # Şifre doğrulandıktan sonra söylenir (hesap varlığı sızmaz) ve başarısızlık sayılmaz.
    if not user.is_approved:
        raise PermissionDeniedError(PENDING_APPROVAL)

    audit.record(db, actor_id=user.id, action="auth.login", entity_type="user", entity_id=user.id)
    db.commit()
    return user


def register(
    db: Session,
    *,
    email: str,
    full_name: str,
    password: str,
    client_key: str,
    account_type: str = "seeker",
) -> User:
    if register_rate_limiter.is_blocked(client_key):
        raise TooManyRequestsError(
            "Çok fazla kayıt denemesi. Lütfen bir dakika sonra tekrar deneyin."
        )
    register_rate_limiter.record_failure(client_key)
    is_recruiter = account_type == "recruiter"
    return users.create_user(
        db,
        email=email,
        full_name=full_name,
        password=password,
        role=UserRole.RECRUITER if is_recruiter else UserRole.SEEKER,
        actor_id=None,
        is_approved=not is_recruiter,
    )
