from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "LandslideSOS API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./landslidesos.db"
    AUTO_CREATE_TABLES: bool = True

    SECRET_KEY: str = "dev-only-change-me-in-prod-0123456789abcdef"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    JWT_ALGORITHM: str = "HS256"

    SMS_PROVIDER: str = "mock"
    MSG91_AUTH_KEY: str = ""
    MSG91_SENDER_ID: str = "LSLSOS"
    MSG91_TEMPLATE_ID: str = ""

    SMS_MAX_PER_ZONE_PER_HOUR: int = 3
    SMS_RECIPIENT_LIMIT: int = 200

    IMD_API_KEY: str = ""
    IMD_API_BASE_URL: str = "https://api.imd.gov.in"

    OPENTOPOGRAPHY_API_KEY: str = ""

    DATA_DIR: str = str(Path(__file__).resolve().parent.parent / "data")
    MODEL_DIR: str = str(Path(__file__).resolve().parent.parent / "models")
    MODEL_PATH: str = str(Path(__file__).resolve().parent.parent / "models" / "risk_model.joblib")
    MODEL_VERSION: str = "2026.09.15"

    CELERY_BROKER_URL: str = "sqlalchemy+sqlite:///celery_broker.db"
    CELERY_RESULT_BACKEND: str = "rpc://"
    CELERY_RECONCILE_MINUTES: int = 30

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()