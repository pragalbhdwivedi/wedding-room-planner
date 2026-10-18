from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLANNER_")
    database_host: str = "db"
    database_name: str = "planner"
    database_user: str = "planner_app"
    database_password_file: str = "/run/secrets/db_app_password"
    bootstrap_token_file: str = "/run/secrets/bootstrap_token"
    cookie_secure: bool = True
    mode: str = "production"
    allowed_origins: str = "https://localhost"
    session_hours: int = 8
    revision: str = "development"

    @property
    def origins(self) -> set[str]:
        return {item.strip().rstrip("/") for item in self.allowed_origins.split(",") if item.strip()}

    def validate_transport(self) -> None:
        if not self.origins:
            raise ValueError("At least one trusted origin is required")
        if self.mode == "production":
            if not self.cookie_secure or any(urlparse(o).scheme != "https" for o in self.origins):
                raise ValueError("Production requires HTTPS origins and secure cookies")
        elif self.mode == "local":
            if any(urlparse(o).hostname not in {"localhost", "127.0.0.1", "::1"} for o in self.origins):
                raise ValueError("Local mode requires loopback trusted origins")
        elif self.mode != "test":
            raise ValueError("Unknown application mode")

    def database_url(self) -> URL:
        password = Path(self.database_password_file).read_text().strip()
        if len(password) < 24:
            raise ValueError("Database secret is missing or too short")
        return URL.create("postgresql+psycopg", username=self.database_user, password=password,
                          host=self.database_host, database=self.database_name)


@lru_cache
def settings() -> Settings:
    result = Settings()
    result.validate_transport()
    return result
