from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AuthenticationError, TooManyRequestsError
from app.core.security import login_rate_limiter, verify_password_or_dummy
from app.models.user import User
from app.services import audit

INVALID_CREDENTIALS = "E-posta veya şifre hatalı"


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

    audit.record(db, actor_id=user.id, action="auth.login", entity_type="user", entity_id=user.id)
    db.commit()
    return user
