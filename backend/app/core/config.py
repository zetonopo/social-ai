from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    sentry_dsn: str = ""
    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
