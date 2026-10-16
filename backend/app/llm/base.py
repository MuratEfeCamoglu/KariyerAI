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


class LLMClient(Protocol):
    """Servislerin gördüğü tek LLM arayüzü; somut istemciye yalnızca factory erişir."""

    @property
    def model_name(self) -> str: ...

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        """CV metninden ParsedCV biçiminde ham JSON döner; doğrulama çağıranın işidir."""
        ...
