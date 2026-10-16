import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Protocol

PROMPTS_DIR = Path(__file__).parent / "prompts"
PARSE_PROMPT_VERSION = "parse_v1"
SCORE_PROMPT_VERSION = "score_v1"

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class LLMError(Exception):
    """LLM çağrısı başarısız oldu (ağ, zaman aşımı, sağlayıcı hatası)."""


class LLMOutputError(LLMError):
    """Model yanıt verdi ama çıktı kullanılamaz (kesik/bozuk JSON). Yeniden denenebilir."""


class LLMRefusalError(LLMError):
    """Model güvenlik gerekçesiyle yanıt vermedi."""


@dataclass(frozen=True)
class Prompt:
    version: str
    system: str
    user_template: str

    def render_user(self, **values: str) -> str:
        # Tek geçişte yalnızca şablondaki yer tutucular doldurulur: str.format CV'deki "{" "}"
        # ile bozulur; sırayla replace ise bir değerin içindeki "{cv_text}" metnini de doldururdu.
        return _PLACEHOLDER.sub(lambda m: values.get(m[1], m[0]), self.user_template)


@cache
def load_prompt(version: str) -> Prompt:
    """`prompts/<version>.md` dosyasını `## system` ve `## user` bölümlerine ayırır."""
    raw = (PROMPTS_DIR / f"{version}.md").read_text(encoding="utf-8")
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in raw.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    try:
        return Prompt(
            version=version,
            system="\n".join(sections["system"]).strip(),
            user_template="\n".join(sections["user"]).strip(),
        )
    except KeyError as exc:
        raise ValueError(f"{version}.md içinde '## {exc.args[0]}' bölümü yok") from exc


# Yapılandırılmış çıktı şeması (sağlayıcıdan bağımsız): modelin ürettiği JSON bu yapıya uyar. Tarih
# biçimi gibi ince kurallar yine de ParsedCV ile doğrulanır. Korunan özellikler (yaş, cinsiyet vb.)
# şemada yoktur (F5b). total_experience_years LLM'e sorulmaz; kodda hesaplanır.
_NULLABLE_STRING: dict[str, Any] = {"type": ["string", "null"]}

PARSED_CV_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "full_name",
        "email",
        "phone",
        "summary",
        "skills",
        "experiences",
        "education",
        "languages",
    ],
    "properties": {
        "full_name": _NULLABLE_STRING,
        "email": _NULLABLE_STRING,
        "phone": _NULLABLE_STRING,
        "summary": _NULLABLE_STRING,
        "skills": {"type": "array", "items": {"type": "string"}},
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "company", "start", "end", "description"],
                "properties": {
                    "title": {"type": "string"},
                    "company": _NULLABLE_STRING,
                    "start": _NULLABLE_STRING,
                    "end": _NULLABLE_STRING,
                    "description": _NULLABLE_STRING,
                },
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["level", "field", "school", "end_year"],
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": ["none", "high_school", "associate", "bachelor", "master", "phd"],
                    },
                    "field": _NULLABLE_STRING,
                    "school": _NULLABLE_STRING,
                    "end_year": {"type": ["integer", "null"]},
                },
            },
        },
        "languages": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["language", "level"],
                "properties": {
                    "language": {"type": "string"},
                    "level": {
                        "type": ["string", "null"],
                        "enum": ["A1", "A2", "B1", "B2", "C1", "C2", None],
                    },
                },
            },
        },
    },
}


def render_score_input(
    prompt: Prompt, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
) -> str:
    """score_v1 kullanıcı mesajı; sağlayıcıdan bağımsız, aynı girdi aynı metni üretir."""
    return prompt.render_user(
        criteria=json.dumps(criteria, ensure_ascii=False, indent=2),
        profile=json.dumps(profile, ensure_ascii=False, indent=2),
        cv_text=anonymized_cv,
    )


# Puanlama çıktısı: kriter başına karşılandı mı + kanıt; sayı alanı yoktur (F6b, puan kodda).
SCORE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["criteria", "summary"],
    "properties": {
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "met", "evidence", "candidate_level"],
                "properties": {
                    "id": {"type": "string"},
                    "met": {"type": "boolean"},
                    "evidence": _NULLABLE_STRING,
                    "candidate_level": {
                        "type": ["string", "null"],
                        "enum": ["A1", "A2", "B1", "B2", "C1", "C2", None],
                    },
                },
            },
        },
        "summary": {"type": "string"},
    },
}


def parse_json_object(text: str | None) -> dict[str, Any]:
    """Modelin metin çıktısını JSON nesnesine çevirir; kullanılamazsa LLMOutputError."""
    if text is None:
        raise LLMOutputError("Yanıtta metin yok")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMOutputError("Yanıt geçerli JSON değil") from exc
    if not isinstance(data, dict):
        raise LLMOutputError("Yanıt bir JSON nesnesi değil")
    return data


class LLMClient(Protocol):
    """Servislerin gördüğü tek LLM arayüzü; somut istemciye yalnızca factory erişir."""

    @property
    def model_name(self) -> str: ...

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        """CV metninden ParsedCV biçiminde ham JSON döner; doğrulama çağıranın işidir."""
        ...

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        """Kriter başına {id, met, evidence, candidate_level} + Türkçe özet döner; puan üretmez."""
        ...
