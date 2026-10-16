from typing import Any

import pytest

from app.core.errors import translate_validation_errors


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ({"type": "missing"}, "Bu alan zorunlu"),
        ({"type": "string_too_short", "ctx": {"min_length": 1}}, "Bu alan boş bırakılamaz"),
        ({"type": "string_too_short", "ctx": {"min_length": 3}}, "En az 3 karakter olmalı"),
        ({"type": "string_too_long", "ctx": {"max_length": 120}}, "En fazla 120 karakter olabilir"),
        ({"type": "too_short", "ctx": {"min_length": 1}}, "En az 1 öğe eklenmeli"),
        ({"type": "too_long", "ctx": {"max_length": 20}}, "En fazla 20 öğe eklenebilir"),
        ({"type": "greater_than_equal", "ctx": {"ge": 0}}, "En az 0 olmalı"),
        ({"type": "less_than_equal", "ctx": {"le": 40}}, "En fazla 40 olabilir"),
        ({"type": "int_from_float"}, "Tam sayı olmalı"),
        (
            {"type": "enum", "ctx": {"expected": "'open' or 'closed'"}},
            "Geçersiz değer. Geçerli değerler: 'open' or 'closed'",
        ),
        (
            {"type": "value_error", "msg": "Value error, Şifre en az 10 karakter olmalı"},
            "Şifre en az 10 karakter olmalı",
        ),
        (
            {"type": "value_error", "msg": "value is not a valid email address: missing @"},
            "Geçerli bir e-posta adresi girin",
        ),
        ({"type": "unknown_type", "msg": "orijinal mesaj"}, "orijinal mesaj"),
    ],
)
def test_translates_known_error_types(error: dict[str, Any], expected: str) -> None:
    [translated] = translate_validation_errors([{"loc": ("body", "x"), **error}])

    assert translated["msg"] == expected
    assert translated["loc"] == ["body", "x"]


def test_drops_submitted_input() -> None:
    [translated] = translate_validation_errors(
        [{"loc": ("body", "password"), "type": "string_too_short", "input": "gizli"}]
    )

    assert "input" not in translated
    assert "gizli" not in str(translated)
