import re
from typing import Any

from app.services.text import fold

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


def _level_after(line: str, language: str) -> str | None:
    # "English (C1), German (A2)": seviye dil adının hemen ardından okunur, satırdaki ilk değil.
    pattern = re.escape(fold(language)) + r"\s*[(:\-–—]?\s*([abc][12])\b"
    match = re.search(pattern, fold(line))
    return match.group(1).upper() if match else None


def _line_mentioning(lines: list[str], label: str) -> str | None:
    pattern = re.compile(r"(?<!\w)" + re.escape(fold(label)) + r"(?!\w)")
    return next((line for line in lines if pattern.search(fold(line))), None)


def _profile_level(profile: dict[str, Any], language: str) -> str | None:
    for item in profile.get("languages", []):
        if fold(str(item.get("language", ""))) == fold(language):
            level = item.get("level")
            return str(level) if level else None
    return None


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

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        """CV'de geçen ilan kriterini "karşılandı" sayar, geçtiği satırı kanıt olarak döner."""
        lines = [line.strip() for line in anonymized_cv.splitlines() if line.strip()]
        answers: list[dict[str, Any]] = []
        for criterion in criteria:
            evidence = _line_mentioning(lines, criterion["label"])
            level: str | None = None
            if criterion["kind"] == "language":
                label = criterion["label"]
                level = (_level_after(evidence, label) if evidence else None) or _profile_level(
                    profile, label
                )
            answers.append(
                {
                    "id": criterion["id"],
                    "met": evidence is not None,
                    "evidence": evidence,
                    "candidate_level": level,
                }
            )
        met = sum(1 for answer in answers if answer["met"])
        return {
            "criteria": answers,
            "summary": (
                f"CV, değerlendirilen {len(answers)} kriterin {met} tanesi için metinde kanıt "
                "içeriyor. Bu özet test amaçlı sahte istemci tarafından üretilmiştir."
            ),
        }
