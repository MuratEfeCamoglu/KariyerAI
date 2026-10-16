import pytest

from app.services.text import fold


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("İngilizce", "ingilizce"),
        ("INGILIZCE", "ingilizce"),
        ("ışık", "IŞIK"),
        ("Python", "python"),
        ("  Makine   Öğrenmesi ", "makine öğrenmesi"),
    ],
)
def test_fold_treats_variants_as_equal(left: str, right: str) -> None:
    assert fold(left) == fold(right)


def test_fold_keeps_distinct_words_distinct() -> None:
    assert fold("Java") != fold("JavaScript")
