import re
from typing import Any

# Deterministik, ağa çıkmayan istemci: testler ve API anahtarsız yerel çalışma için (CLAUDE.md).
# Gerçek bir ayrıştırıcı değildir; sentetik test CV'lerindeki etiketli satırları okur.

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"\+?\d[\d ()-]{8,}\d")
_SKILL_LABELS = ("skills", "beceriler", "yetenekler")
_LANGUAGE_LABELS = ("languages", "diller")
_LANGUAGE_ITEM = re.compile(r"^(?P<name>.+?)\s*[(\-–]\s*(?P<level>[ABC][12])\s*\)?$")


def _labelled_items(lines: list[str], labels: tuple[str, ...]) -> list[str]:
    for line in lines:
        label, sep, rest = line.partition(":")
        if sep and label.strip().casefold() in labels:
            return [item.strip() for item in re.split(r"[,;]", rest) if item.strip()]
    return []


def _languages(items: list[str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        match = _LANGUAGE_ITEM.match(item)
        if match:
            result.append({"language": match["name"].strip(), "level": match["level"]})
        else:
            result.append({"language": item, "level": None})
    return result


class FakeLLMClient:
    model_name = "fake"

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        lines = [line.strip() for line in cv_text.splitlines() if line.strip()]
        first = lines[0] if lines else ""
        email = _EMAIL.search(cv_text)
        phone = _PHONE.search(cv_text)
        return {
            "full_name": first if first and ":" not in first and len(first) <= 60 else None,
            "email": email.group(0) if email else None,
            "phone": phone.group(0).strip() if phone else None,
            "summary": None,
            "skills": _labelled_items(lines, _SKILL_LABELS),
            "experiences": [],
            "education": [],
            "languages": _languages(_labelled_items(lines, _LANGUAGE_LABELS)),
        }
