from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env.example'daki örnek anahtar; canlıda (COOKIE_SECURE=true) kullanılması engellenir.
EXAMPLE_JWT_SECRET = "dev-only-change-me-0123456789abcdef"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/kariyerai.db"
    jwt_secret: SecretStr = Field(min_length=32)
    llm_provider: Literal["anthropic", "gemini", "groq", "fake"] = "fake"
    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-sonnet-5-5"
    # Gemini ücretsiz katmanı yalnızca sentetik veriyle (eval/test) kullanılır: gönderilen içerik
    # sağlayıcının ürün geliştirmesinde kullanılabilir (KVKK, ISKELET V2).
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash"
    # Groq ücretsiz katmanı da yalnızca sentetik veriyle kullanılır (ISKELET V2).
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    upload_dir: Path = Path("./data/uploads")
    # HTTPS arkasında true: oturum cookie'si yalnızca HTTPS ile gönderilir (ISKELET V10).
    cookie_secure: bool = False

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
