import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Protocol

PROMPTS_DIR = Path(__file__).parent / "prompts"
PARSE_PROMPT_VERSION = "parse_v1"


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
        # str.format kullanılmaz: CV metnindeki "{" "}" karakterleri biçimlendirmeyi bozar.
        text = self.user_template
        for key, value in values.items():
            text = text.replace("{" + key + "}", value)
        return text


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
