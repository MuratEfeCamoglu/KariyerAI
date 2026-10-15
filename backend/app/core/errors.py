class DomainError(Exception):
    """Servis katmanının fırlattığı, HTTP'den bağımsız hata. `main.py` HTTP koduna çevirir."""

    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class PermissionDeniedError(DomainError):
    status_code = 403
