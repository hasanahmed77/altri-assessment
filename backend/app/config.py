from functools import cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MODEL = "gpt-4.1-mini"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/str"
    openai_api_key: str = ""
    openai_model: str = DEFAULT_MODEL

    @field_validator("database_url")
    @classmethod
    def use_psycopg3_driver(cls, url: str) -> str:
        # Supabase hands out postgresql:// URLs; SQLAlchemy would pick psycopg2 for those
        return url.replace("postgresql://", "postgresql+psycopg://", 1)

    @field_validator("openai_model")
    @classmethod
    def default_when_blank(cls, model: str) -> str:
        # docker compose passes an unset variable through as an empty string
        return model.strip() or DEFAULT_MODEL


@cache
def get_settings() -> Settings:
    return Settings()
