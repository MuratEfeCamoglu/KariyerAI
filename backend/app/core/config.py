from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env.example'daki örnek anahtar; canlıda (COOKIE_SECURE=true) kullanılması engellenir.
EXAMPLE_JWT_SECRET = "dev-only-change-me-0123456789abcdef"
LLM_PROVIDERS = ("groq", "gemini", "fake")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/kariyerai.db"
    jwt_secret: SecretStr = Field(min_length=32)
    # Tek sağlayıcı ("groq") ya da öncelik sırasıyla liste ("gemini,groq"): birincinin kotası
    # dolunca sıradaki kullanılır.
    llm_provider: str = "fake"
    # Gerçek aday verisi de gönderilir (ISKELET V2); ücretsiz katman koşulları: README, R3.
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash"
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    upload_dir: Path = Path("./data/uploads")
    # HTTPS arkasında true: oturum cookie'si yalnızca HTTPS ile gönderilir (ISKELET V10).
    cookie_secure: bool = False

    @field_validator("llm_provider")
    @classmethod
    def _validate_llm_provider(cls, value: str) -> str:
        providers = [item.strip() for item in value.split(",")]
        unknown = [item for item in providers if item not in LLM_PROVIDERS]
        if unknown or len(set(providers)) != len(providers):
            raise ValueError(
                f"LLM_PROVIDER yalnızca {', '.join(LLM_PROVIDERS)} değerlerinden oluşan, "
                "tekrarsız ve virgülle ayrılmış bir liste olabilir"
            )
        return ",".join(providers)

    @property
    def llm_providers(self) -> list[str]:
        return self.llm_provider.split(",")

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
