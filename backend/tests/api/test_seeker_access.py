import pytest
from fastapi.testclient import TestClient

STAFF_ENDPOINTS = [
    ("GET", "/api/jobs"),
    ("POST", "/api/jobs"),
    ("GET", "/api/jobs/1"),
    ("PATCH", "/api/jobs/1"),
    ("DELETE", "/api/jobs/1"),
    ("POST", "/api/jobs/1/rescore"),
    ("GET", "/api/jobs/1/applications"),
    ("POST", "/api/jobs/1/cvs"),
    ("GET", "/api/applications/1"),
    ("PATCH", "/api/applications/1/status"),
    ("POST", "/api/applications/1/notes"),
    ("POST", "/api/applications/1/retry"),
    ("DELETE", "/api/notes/1"),
    ("GET", "/api/candidates/1/cv"),
    ("DELETE", "/api/candidates/1"),
    ("GET", "/api/users"),
    ("GET", "/api/audit"),
]


@pytest.mark.parametrize(("method", "path"), STAFF_ENDPOINTS)
def test_seeker_forbidden_on_staff_endpoints(
    seeker_client: TestClient, method: str, path: str
) -> None:
    response = seeker_client.request(method, path)

    assert response.status_code == 403, response.text
