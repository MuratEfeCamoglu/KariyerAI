from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "sqlite:///./data/kariyerai.db"
    jwt_secret: SecretStr = Field(min_length=32)
    llm_provider: Literal["anthropic", "gemini", "fake"] = "fake"
    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-sonnet-5-5"
    # Gemini ücretsiz katmanı yalnızca sentetik veriyle (eval/test) kullanılır: gönderilen içerik
    # sağlayıcının ürün geliştirmesinde kullanılabilir (KVKK, ISKELET V2).
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash"
    upload_dir: Path = Path("./data/uploads")


@lru_cache
def get_settings() -> Settings:
    return Settings()
