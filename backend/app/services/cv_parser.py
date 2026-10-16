import logging
from datetime import date

from pydantic import ValidationError

from app.llm.base import LLMClient, LLMOutputError
from app.schemas.parsed_cv import ParsedCV
from app.services.experience import total_experience_years

logger = logging.getLogger(__name__)

# Maliyet ve bağlam sınırı için (ISKELET R6): fazlası LLM'e gönderilmez.
MAX_LLM_CHARS = 30_000
# F5a: doğrulama başarısızsa 1 kez yeniden denenir.
MAX_ATTEMPTS = 2


def parse_cv(cv_text: str, llm: LLMClient, today: date | None = None) -> ParsedCV:
    """CV metnini yapılandırır.

    Çıktı ParsedCV şemasına uymazsa (ya da kesik/bozuk gelirse) bir kez yeniden dener; ikinci
    denemede de olmazsa son hatayı yükseltir. Ağ/sağlayıcı hatası (LLMError) burada yeniden
    denenmez: SDK zaten üstel beklemeyle dener.
    """
    text = cv_text[:MAX_LLM_CHARS]
    last_error: ValidationError | LLMOutputError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            parsed = ParsedCV.model_validate(llm.parse_cv(text))
        except (ValidationError, LLMOutputError) as exc:
            last_error = exc
            # Hata metni CV içeriği taşıyabilir; yalnızca tür ve deneme sayısı loglanır.
            logger.info("Ayrıştırma çıktısı geçersiz (deneme %s): %s", attempt, type(exc).__name__)
            continue
        parsed.total_experience_years = total_experience_years(
            parsed.experiences, today or date.today()
        )
        return parsed
    assert last_error is not None
    raise last_error
