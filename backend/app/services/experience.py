from datetime import date

from app.schemas.parsed_cv import Experience


def _month_index(year_month: str) -> int:
    year, month = year_month.split("-")
    return int(year) * 12 + int(month) - 1


def total_experience_years(experiences: list[Experience], today: date) -> float:
    """ISKELET §3.4: deneyim yılı LLM'den değil, tarihlerden hesaplanır.

    - Ay bazında, başlangıç ve bitiş ayı dahil sayılır.
    - Çakışan dönemler bir kez sayılır.
    - "present" = bu ay; başlangıcı olmayan deneyim sayılmaz.
    - Bitişi bilinmeyen (null) deneyim yalnızca başlangıç ayı olarak sayılır (varsayım: süre
      kanıtlanamıyorsa fazla saymamak, adayı haksız yere öne çıkarmamak için).
    - Gelecekte başlayan ya da bitişi başlangıcından önce olan kayıtlar yok sayılır.
    """
    current = today.year * 12 + today.month - 1
    intervals: list[tuple[int, int]] = []
    for experience in experiences:
        if experience.start is None:
            continue
        start = _month_index(experience.start)
        if experience.end == "present":
            end = current
        elif experience.end is None:
            end = start
        else:
            end = _month_index(experience.end)
        end = min(end, current)
        if start > end:
            continue
        intervals.append((start, end))

    months = 0
    merged_end = -1
    for start, end in sorted(intervals):
        if end <= merged_end:
            continue
        months += end - max(start, merged_end + 1) + 1
        merged_end = end
    return round(months / 12, 1)
