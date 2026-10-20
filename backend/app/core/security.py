import threading
import time
from collections import deque
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings

BCRYPT_COST = 12
ACCESS_TOKEN_TTL = timedelta(hours=8)
JWT_ALGORITHM = "HS256"
AUTH_COOKIE_NAME = "access_token"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_COST)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# Bilinmeyen e-postada da bcrypt çalıştırılır; yanıt süresinden kayıtlı e-posta anlaşılmasın.
_DUMMY_HASH = hash_password("timing-equalizer-password")


def verify_password_or_dummy(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        verify_password(password, _DUMMY_HASH)
        return False
    return verify_password(password, password_hash)


def create_access_token(user_id: int, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": issued_at, "exp": issued_at + ACCESS_TOKEN_TTL}
    secret = get_settings().jwt_secret.get_secret_value()
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Geçerli token'daki kullanıcı id'sini döner; süresi dolmuş/bozuk token için None."""
    secret = get_settings().jwt_secret.get_secret_value()
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


class LoginRateLimiter:
    """IP başına kayan pencerede başarısız giriş sayacı (tek süreç, bellek içi — ISKELET §5)."""

    def __init__(self, max_failures: int = 10, window_seconds: float = 60.0) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._failures.setdefault(key, deque())
        while attempts and now - attempts[0] >= self.window_seconds:
            attempts.popleft()
        return attempts

    def is_blocked(self, key: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        with self._lock:
            return len(self._prune(key, current)) >= self.max_failures

    def record_failure(self, key: str, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        with self._lock:
            self._prune(key, current).append(current)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_rate_limiter = LoginRateLimiter()
# Herkese açık kayıt ucu: başarılı ya da başarısız her deneme sayılır (toplu hesap açmayı keser).
register_rate_limiter = LoginRateLimiter(max_failures=5)
