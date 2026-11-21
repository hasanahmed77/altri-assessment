from functools import cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/str"
    openai_api_key: str = ""
    openai_model: str = ""

    @field_validator("database_url")
    @classmethod
    def use_psycopg3_driver(cls, url: str) -> str:
        # Supabase hands out postgresql:// URLs; SQLAlchemy would pick psycopg2 for those
        return url.replace("postgresql://", "postgresql+psycopg://", 1)


@cache
def get_settings() -> Settings:
    return Settings()
