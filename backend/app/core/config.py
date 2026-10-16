from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env.example'daki örnek anahtar; canlıda (COOKIE_SECURE=true) kullanılması engellenir.
EXAMPLE_JWT_SECRET = "dev-only-change-me-0123456789abcdef"
LLM_PROVIDERS = ("groq", "gemini", "fake")


def _split(value: str) -> list[str]:
    return [item.strip() for item in value.split(",")]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/kariyerai.db"
    jwt_secret: SecretStr = Field(min_length=32)
    # Tek sağlayıcı ("groq") ya da öncelik sırasıyla liste ("gemini,groq"): birincinin kotası
    # dolunca sıradaki kullanılır.
    llm_provider: str = "fake"
    # Boşsa LLM_PROVIDER kullanılır. Kotası küçük sağlayıcıyı tek işe ayırmak için
    # (ör. ayrıştırma groq,gemini · puanlama gemini,groq): Gemini CV başına bir istek harcar.
    llm_parse_provider: str | None = None
    llm_score_provider: str | None = None
    # Gerçek aday verisi de gönderilir (ISKELET V2); ücretsiz katman koşulları: README, R3.
    gemini_api_key: SecretStr | None = None
    # Tek model ya da sıralı liste: ücretsiz kota model başınadır, biri dolunca sıradaki denenir.
    gemini_model: str = "gemini-3.5-flash"
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    upload_dir: Path = Path("./data/uploads")
    # HTTPS arkasında true: oturum cookie'si yalnızca HTTPS ile gönderilir (ISKELET V10).
    cookie_secure: bool = False

    @field_validator("llm_parse_provider", "llm_score_provider", mode="before")
    @classmethod
    def _empty_means_default(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("llm_provider", "llm_parse_provider", "llm_score_provider")
    @classmethod
    def _validate_llm_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        providers = _split(value)
        unknown = [item for item in providers if item not in LLM_PROVIDERS]
        if unknown or len(set(providers)) != len(providers):
            raise ValueError(
                f"LLM_PROVIDER yalnızca {', '.join(LLM_PROVIDERS)} değerlerinden oluşan, "
                "tekrarsız ve virgülle ayrılmış bir liste olabilir"
            )
        return ",".join(providers)

    @field_validator("gemini_model")
    @classmethod
    def _validate_gemini_model(cls, value: str) -> str:
        models = _split(value)
        if not all(models) or len(set(models)) != len(models):
            raise ValueError(
                "GEMINI_MODEL boş olmayan, tekrarsız ve virgülle ayrılmış liste olmalı"
            )
        return ",".join(models)

    @property
    def llm_providers(self) -> list[str]:
        return self.llm_provider.split(",")

    @property
    def parse_providers(self) -> list[str]:
        return (self.llm_parse_provider or self.llm_provider).split(",")

    @property
    def score_providers(self) -> list[str]:
        return (self.llm_score_provider or self.llm_provider).split(",")

    @property
    def gemini_models(self) -> list[str]:
        return self.gemini_model.split(",")

    @model_validator(mode="after")
    def _reject_example_secret_in_production(self) -> "Settings":
        if self.cookie_secure and self.jwt_secret.get_secret_value() == EXAMPLE_JWT_SECRET:
            raise ValueError(
                "COOKIE_SECURE=true iken .env.example'daki örnek JWT_SECRET kullanılamaz; "
                "rastgele, en az 32 karakterlik bir değer üretin."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
