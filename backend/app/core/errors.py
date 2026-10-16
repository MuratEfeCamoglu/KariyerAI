from collections.abc import Iterable, Mapping, Sequence
from typing import Any


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


class FieldValidationError(DomainError):
    """Yalnızca serviste bilinebilen alan hatası (ör. kayıtlı veriyle çakışma).

    Pydantic'in 422'siyle aynı biçimde döner; arayüz hatayı ilgili alanın altında gösterir.
    """

    status_code = 422

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field

    def as_errors(self) -> list[dict[str, Any]]:
        return [{"loc": ["body", self.field], "msg": self.detail, "type": "value_error"}]


def _count_msg(ctx: Mapping[str, Any], key: str, template: str) -> str:
    return template.format(n=ctx.get(key, "?"))


def _translate_message(error: Mapping[str, Any]) -> str:
    kind = str(error.get("type", ""))
    ctx: Mapping[str, Any] = error.get("ctx") or {}
    msg = str(error.get("msg", ""))

    if kind == "missing":
        return "Bu alan zorunlu"
    if kind == "string_too_short":
        if ctx.get("min_length") == 1:
            return "Bu alan boş bırakılamaz"
        return _count_msg(ctx, "min_length", "En az {n} karakter olmalı")
    if kind == "string_too_long":
        return _count_msg(ctx, "max_length", "En fazla {n} karakter olabilir")
    if kind == "too_short":
        return _count_msg(ctx, "min_length", "En az {n} öğe eklenmeli")
    if kind == "too_long":
        return _count_msg(ctx, "max_length", "En fazla {n} öğe eklenebilir")
    if kind in {"greater_than_equal", "greater_than"}:
        return _count_msg(ctx, "ge" if "ge" in ctx else "gt", "En az {n} olmalı")
    if kind in {"less_than_equal", "less_than"}:
        return _count_msg(ctx, "le" if "le" in ctx else "lt", "En fazla {n} olabilir")
    if kind in {"int_parsing", "int_from_float", "int_type"}:
        return "Tam sayı olmalı"
    if kind in {"enum", "literal_error"}:
        return f"Geçersiz değer. Geçerli değerler: {ctx.get('expected', '')}".rstrip(": ")
    if kind == "string_type":
        return "Metin olmalı"
    if kind == "list_type":
        return "Liste olmalı"
    if kind in {"bool_type", "bool_parsing"}:
        return "Evet/hayır değeri olmalı"
    if kind in {"model_type", "model_attributes_type", "dict_type"}:
        return "Geçersiz nesne"
    if kind == "json_invalid":
        return "Geçersiz JSON"
    if kind == "value_error":
        if msg.startswith("value is not a valid email address"):
            return "Geçerli bir e-posta adresi girin"
        return msg.removeprefix("Value error, ")
    return msg


def translate_validation_errors(errors: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """FastAPI 422 hatalarını Türkçeleştirir.

    `input` alanı bilinçli olarak atılır: gönderilen değer (ör. şifre) yanıtta geri dönmesin.
    """
    translated: list[dict[str, Any]] = []
    for error in errors:
        loc: Sequence[Any] = error.get("loc", ())
        translated.append(
            {"loc": list(loc), "msg": _translate_message(error), "type": error.get("type")}
        )
    return translated
