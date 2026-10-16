from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_turkish_404(client: TestClient) -> None:
    response = client.get("/api/olmayan-yol")

    assert response.status_code == 404
    assert response.json() == {"detail": "Kaynak bulunamadı"}


def test_wrong_method_returns_turkish_405(client: TestClient) -> None:
    response = client.put("/api/health")

    assert response.status_code == 405
    assert response.json() == {"detail": "Bu işlem desteklenmiyor"}


def test_undecodable_body_returns_turkish_400(recruiter_client: TestClient) -> None:
    # Windows kod sayfasıyla (UTF-8 olmayan) gönderilmiş Türkçe karakter.
    response = recruiter_client.post(
        "/api/jobs",
        content='{"title": "Kıdemli"}'.encode("cp1254"),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "İstek gövdesi okunamadı"}
