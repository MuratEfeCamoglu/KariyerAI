"""Sağlayıcıları sırayla deneyen istemci: birincinin kotası dolunca sıradakine geçer.

Ücretsiz katmanların günlük/dakikalık kotaları küçüktür (README); `LLM_PROVIDER=gemini,groq`
ile Gemini'nin kotası bitince Groq kullanılır, bekleme süresi dolunca Gemini'ye geri dönülür.
"""

import logging
import threading
import time
from collections.abc import Callable, Sequence
from typing import Any

from app.llm.base import LLMClient, LLMError, LLMOutputError, LLMRateLimitError, LLMRefusalError

logger = logging.getLogger(__name__)

# Sağlayıcı bekleme süresi bildirmezse 429 sonrası bu kadar atlanır.
DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS = 60.0
# 5xx/ağ hatasında (istemci kendi yeniden denemelerini zaten yaptı) kısa süre atlanır.
ERROR_COOLDOWN_SECONDS = 30.0
# Günlük kota dolduğunda bildirilen bekleme saatlerce olabilir; bir günden uzun beklenmez.
MAX_COOLDOWN_SECONDS = 24 * 60 * 60.0


class FallbackLLMClient:
    def __init__(
        self, clients: Sequence[LLMClient], clock: Callable[[], float] = time.monotonic
    ) -> None:
        if not clients:
            raise ValueError("En az bir LLM istemcisi gerekir")
        self._clients = list(clients)
        self._clock = clock
        self._lock = threading.Lock()
        self._cooldown_until = [0.0] * len(self._clients)
        # Arka plan işleri ayrı thread'lerde çalışır; her thread kendi çağrısına hizmet eden
        # modeli görmeli (pipeline ve puanlama `model_name`'i çağrıdan sonra okur, audit'e yazar).
        self._served = threading.local()

    @property
    def model_name(self) -> str:
        served: str | None = getattr(self._served, "model", None)
        return served if served is not None else self._clients[0].model_name

    def parse_cv(self, cv_text: str) -> dict[str, Any]:
        return self._call(lambda client: client.parse_cv(cv_text))

    def score_cv(
        self, anonymized_cv: str, criteria: list[dict[str, str]], profile: dict[str, Any]
    ) -> dict[str, Any]:
        return self._call(lambda client: client.score_cv(anonymized_cv, criteria, profile))

    def _order(self) -> list[int]:
        """Beklemede olmayanlar öncelik sırasıyla; hepsi beklemedeyse en erken açılan."""
        now = self._clock()
        with self._lock:
            ready = [i for i, until in enumerate(self._cooldown_until) if until <= now]
            if ready:
                return ready
            return [min(range(len(self._clients)), key=lambda i: self._cooldown_until[i])]

    def _cool_down(self, index: int, seconds: float) -> None:
        until = self._clock() + min(seconds, MAX_COOLDOWN_SECONDS)
        with self._lock:
            self._cooldown_until[index] = max(self._cooldown_until[index], until)

    def _call(self, call: Callable[[LLMClient], dict[str, Any]]) -> dict[str, Any]:
        last_error: LLMError | None = None
        for index in self._order():
            client = self._clients[index]
            try:
                result = call(client)
            except LLMOutputError:
                # Model yanıt verdi; çıktı bozuk. Çağıran taraf zaten bir kez yeniden dener.
                raise
            except LLMRateLimitError as exc:
                wait = exc.retry_after
                self._cool_down(
                    index, DEFAULT_RATE_LIMIT_COOLDOWN_SECONDS if wait is None else wait
                )
                last_error = exc
            except LLMRefusalError as exc:
                # İçeriğe özgü; sağlayıcı sağlam, beklemeye alınmaz.
                last_error = exc
            except LLMError as exc:
                self._cool_down(index, ERROR_COOLDOWN_SECONDS)
                last_error = exc
            else:
                self._served.model = client.model_name
                return result
            logger.warning(
                "LLM sağlayıcısı başarısız, sıradakine geçiliyor: model=%s (%s)",
                client.model_name,
                type(last_error).__name__,
            )
        assert last_error is not None
        raise last_error
