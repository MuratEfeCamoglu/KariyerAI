from datetime import date

import pytest

from app.schemas.parsed_cv import Experience
from app.services.experience import total_experience_years

TODAY = date(2026, 10, 16)


def _exp(start: str | None, end: str | None) -> Experience:
    return Experience(title="Pozisyon", start=start, end=end)


@pytest.mark.parametrize(
    ("experiences", "expected"),
    [
        ([], 0.0),
        # Başlangıç ve bitiş ayı dahil: 2020-01..2020-12 = 12 ay.
        ([_exp("2020-01", "2020-12")], 1.0),
        ([_exp("2018-06", "2021-02")], 2.8),  # 33 ay
        # present = bu ay (2026-10): 2026-01..2026-10 = 10 ay.
        ([_exp("2026-01", "present")], 0.8),
        # Çakışan dönemler bir kez sayılır: 2020-01..2021-06 = 18 ay.
        ([_exp("2020-01", "2020-12"), _exp("2020-07", "2021-06")], 1.5),
        # İç içe dönem toplamı artırmaz.
        ([_exp("2019-01", "2021-12"), _exp("2020-03", "2020-05")], 3.0),
        # Aralarında boşluk olan dönemler ayrı ayrı toplanır: 6 + 6 ay.
        ([_exp("2020-01", "2020-06"), _exp("2021-01", "2021-06")], 1.0),
        # Başlangıcı olmayan sayılmaz.
        ([_exp(None, "2020-12")], 0.0),
        # Bitişi bilinmeyen yalnızca başlangıç ayı olarak sayılır.
        ([_exp("2020-01", None)], 0.1),
        # Gelecekte başlayan ve ters tarihli kayıtlar yok sayılır.
        ([_exp("2027-01", "present"), _exp("2022-05", "2021-01")], 0.0),
        # Gelecekteki bitiş tarihi bugüne kırpılır: 2026-01..2026-10.
        ([_exp("2026-01", "2028-12")], 0.8),
    ],
)
def test_total_experience_years(experiences: list[Experience], expected: float) -> None:
    assert total_experience_years(experiences, TODAY) == expected


def test_order_of_experiences_does_not_matter() -> None:
    items = [_exp("2021-01", "present"), _exp("2015-03", "2017-02"), _exp("2016-01", "2021-06")]

    assert total_experience_years(items, TODAY) == total_experience_years(items[::-1], TODAY)
