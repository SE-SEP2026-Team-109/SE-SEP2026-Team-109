from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MentorConnect API"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./mentor.db"
    secret_key: str = "change-me-in-.env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
