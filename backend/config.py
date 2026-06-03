import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "CompetitorLens API"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://competitorlens:competitorlens@localhost:5432/competitorlens",
    )
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC",
        "postgresql://competitorlens:competitorlens@localhost:5432/competitorlens",
    )

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://app.thetransformix.com",
    ]

    # AI / Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    AZURE_OPENAI_MODEL: str = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")

    # Scraping
    MAX_COMPETITORS: int = 5
    REVIEWS_PER_COMPETITOR: int = 100

    # JWT (for future auth)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-please")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Admin defaults
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@competitorlens.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Admin@2024!")
    ADMIN_FULL_NAME: str = os.getenv("ADMIN_FULL_NAME", "Admin")

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
