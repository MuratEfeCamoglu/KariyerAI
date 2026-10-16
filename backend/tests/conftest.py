import os

# Ayarlar modül import edilirken okunduğu için uygulama import'undan önce sabitlenmeli.
os.environ["LLM_PROVIDER"] = "fake"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("JWT_SECRET", "test-secret-0123456789abcdef0123456789")

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import security
from app.core.db import create_db_engine, get_db
from app.core.security import login_rate_limiter
from app.main import app
from app.models import Base, User, UserRole
from app.services import users as users_service

ADMIN_PASSWORD = "admin-password-123"
RECRUITER_PASSWORD = "recruiter-password-123"


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    test_engine = create_db_engine(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    login_rate_limiter.reset()


@pytest.fixture(autouse=True)
def _fast_bcrypt(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    # Cost 12 her hash'te ~250 ms; testler bunu yüzlerce kez yapar. Üretim maliyeti
    # `real_bcrypt` işaretli testlerde ayrıca doğrulanır.
    if request.node.get_closest_marker("real_bcrypt") is None:
        monkeypatch.setattr(security, "BCRYPT_COST", 4)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin(db: Session) -> User:
    return users_service.create_user(
        db,
        email="admin@example.com",
        full_name="Ayşe Yönetici",
        password=ADMIN_PASSWORD,
        role=UserRole.ADMIN,
        actor_id=None,
    )


@pytest.fixture
def recruiter(db: Session) -> User:
    return users_service.create_user(
        db,
        email="ik@example.com",
        full_name="Mehmet Uzman",
        password=RECRUITER_PASSWORD,
        role=UserRole.RECRUITER,
        actor_id=None,
    )


LoginFn = Callable[[str, str], TestClient]


@pytest.fixture
def login(client: TestClient) -> LoginFn:
    def _login(email: str, password: str) -> TestClient:
        response = client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return client

    return _login


@pytest.fixture
def admin_client(admin: User, login: LoginFn) -> TestClient:
    return login(admin.email, ADMIN_PASSWORD)


@pytest.fixture
def recruiter_client(recruiter: User, login: LoginFn) -> TestClient:
    return login(recruiter.email, RECRUITER_PASSWORD)
