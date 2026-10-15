class DomainError(Exception):
    """Servis katmanının fırlattığı, HTTP'den bağımsız hata. `main.py` HTTP koduna çevirir."""

    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ValidationError(DomainError):
    status_code = 400


class AuthenticationError(DomainError):
    status_code = 401


class PermissionDeniedError(DomainError):
    status_code = 403


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class TooManyRequestsError(DomainError):
    status_code = 429
