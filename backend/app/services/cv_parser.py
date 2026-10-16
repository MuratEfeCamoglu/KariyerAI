from app.llm.base import LLMClient
from app.schemas.parsed_cv import ParsedCV

# Maliyet ve bağlam sınırı için (ISKELET R6): fazlası LLM'e gönderilmez.
MAX_LLM_CHARS = 30_000


def parse_cv(cv_text: str, llm: LLMClient) -> ParsedCV:
    """CV metnini yapılandırır. Doğrulama hatasında pydantic.ValidationError yükselir.

    Aşama 4'te: tek seferlik yeniden deneme, gerçek prompt ve deneyim yılı hesabı eklenecek.
    """
    raw = llm.parse_cv(cv_text[:MAX_LLM_CHARS])
    return ParsedCV.model_validate(raw)
