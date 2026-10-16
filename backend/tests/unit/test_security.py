from datetime import UTC, datetime, timedelta

import pytest

from app.core.security import (
    LoginRateLimiter,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
    verify_password_or_dummy,
)


@pytest.mark.real_bcrypt
def test_hash_password_uses_bcrypt_cost_12_and_verifies() -> None:
    hashed = hash_password("guvenli-sifre-1")

    assert hashed.startswith("$2b$12$")
    assert "guvenli-sifre-1" not in hashed
    assert verify_password("guvenli-sifre-1", hashed)
    assert not verify_password("baska-sifre-12", hashed)


def test_verify_password_or_dummy_rejects_missing_user() -> None:
    assert verify_password_or_dummy("herhangi-sifre", None) is False


def test_access_token_roundtrip() -> None:
    assert decode_access_token(create_access_token(42)) == 42


def test_expired_access_token_is_rejected() -> None:
    issued = datetime.now(UTC) - timedelta(hours=8, seconds=1)

    assert decode_access_token(create_access_token(42, now=issued)) is None


def test_garbage_token_is_rejected() -> None:
    assert decode_access_token("not-a-jwt") is None


def test_rate_limiter_blocks_after_max_failures_within_window() -> None:
    limiter = LoginRateLimiter(max_failures=10, window_seconds=60)
    for second in range(10):
        assert not limiter.is_blocked("1.2.3.4", now=float(second))
        limiter.record_failure("1.2.3.4", now=float(second))

    assert limiter.is_blocked("1.2.3.4", now=30.0)
    assert not limiter.is_blocked("5.6.7.8", now=30.0)


def test_rate_limiter_forgets_failures_older_than_window() -> None:
    limiter = LoginRateLimiter(max_failures=10, window_seconds=60)
    for _ in range(10):
        limiter.record_failure("1.2.3.4", now=0.0)

    assert not limiter.is_blocked("1.2.3.4", now=60.0)
