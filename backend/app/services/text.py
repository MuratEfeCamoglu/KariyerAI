import re

# Türkçe/İngilizce karışık metinde "İngilizce", "ingilizce", "INGILIZCE" aynı kabul edilmeli.
# str.casefold() "İ"yi "i̇" (i + birleşik nokta) yaptığı için tek başına yetmez.
_DOTTED_I = str.maketrans({"İ": "i", "I": "i", "ı": "i"})
_WHITESPACE = re.compile(r"\s+")


def fold(text: str) -> str:
    """Harf büyüklüğü, Türkçe i varyantları ve boşluk farkını yok sayan karşılaştırma anahtarı."""
    return _WHITESPACE.sub(" ", text.translate(_DOTTED_I).casefold()).strip()
