"""Puanlama girdisinden kişisel veriyi çıkarır (ISKELET §3.5, F6d).

LLM'e giden metin ve kanıt doğrulaması aynı anonim metin üzerinde yapılır; bu yüzden çıktı
deterministik olmalıdır.
"""

import re

MASK = "[GİZLENDİ]"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(
    r"(?:https?://|www\.)\S+"
    # Şemasız profil bağlantıları: linkedin.com/in/..., github.com/...
    r"|\b[\w-]+(?:\.[\w-]+)*\.(?:com|net|org|io|dev|me|tr)(?:\.[a-z]{2})?/\S*",
    re.IGNORECASE,
)
# +90 555 000 11 22, (0555) 000-11-22, 05550001122 ... — en az 10 rakam.
_PHONE = re.compile(r"(?<!\w)\+?\(?\d(?:[\s().-]*\d){9,14}(?!\w)")
# Gün içeren tarihler doğum tarihi olabilir; deneyim tarihleri (2020-03, 03/2021) gün içermez.
_FULL_DATE = re.compile(
    r"\b(?:\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}|(?:19|20)\d{2}-\d{1,2}-\d{1,2})\b"
)
# Bu etiketlerle başlayan satırların değeri tamamen gizlenir.
_SENSITIVE_LABEL = re.compile(
    r"^(?P<label>\s*(?:doğum\s*tarihi|doğum\s*yeri|date\s*of\s*birth|birth\s*date|d\.o\.b\.?|"
    r"yaş|age|cinsiyet|gender|medeni\s*(?:hal|durum)|marital\s*status|uyruk|nationality|"
    r"din|religion)\s*[:\-–])(?P<value>.*)$",
    re.IGNORECASE | re.MULTILINE,
)
_ADDRESS_LINE = re.compile(r"^\s*(?:adres|address)\b.*$\n?", re.IGNORECASE | re.MULTILINE)


def _name_pattern(full_name: str) -> re.Pattern[str] | None:
    # Ad tam olarak ve parça parça (ör. yalnızca soyad, "D. Arslan") geçebilir.
    parts = [part for part in re.split(r"\s+", full_name.strip()) if len(part) >= 2]
    if not parts:
        return None
    alternatives = [r"\s+".join(map(re.escape, parts)), *map(re.escape, parts)]
    return re.compile(r"(?<!\w)(?:" + "|".join(alternatives) + r")(?!\w)", re.IGNORECASE)


def anonymize(cv_text: str, full_name: str | None) -> str:
    text = _ADDRESS_LINE.sub("", cv_text)
    text = _SENSITIVE_LABEL.sub(lambda m: f"{m['label']} {MASK}", text)
    text = _EMAIL.sub(MASK, text)
    text = _URL.sub(MASK, text)
    text = _PHONE.sub(MASK, text)
    text = _FULL_DATE.sub(MASK, text)
    if full_name:
        pattern = _name_pattern(full_name)
        if pattern is not None:
            text = pattern.sub(MASK, text)
    return text
