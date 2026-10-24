from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str | None = None
    database_hostname: str | None = None
    database_port: int | None = None
    database_password: str | None = None
    database_name: str | None = None
    database_username: str | None = None
    db_pool_size: int = 5
    db_max_overflow: int = 10

    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    login_rate_limit: str = "5/minute"
    rate_limit_enabled: bool = True
    rate_limit_storage_uri: str = "memory://"

    upload_dir: Path = BASE_DIR / "uploads"
    max_photo_bytes: int = 5 * 1024 * 1024
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_endpoint_url: str | None = None
    s3_url_expire_seconds: int = 3600

    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
