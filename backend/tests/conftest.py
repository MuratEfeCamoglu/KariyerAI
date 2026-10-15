import os

# Ayarlar modül import edilirken okunduğu için uygulama import'undan önce sabitlenmeli.
os.environ["LLM_PROVIDER"] = "fake"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("JWT_SECRET", "test-secret-0123456789abcdef0123456789")

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
