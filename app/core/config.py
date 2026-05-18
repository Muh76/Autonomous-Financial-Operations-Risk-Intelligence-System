from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Autonomous Financial Operations & Risk Intelligence Platform"
    app_version: str = "0.1.0"
    app_env: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://finance:finance@localhost:5432/finance_ops"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 1800
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20
    redis_socket_timeout: float = 5.0
    redis_health_check_interval: int = 30
    log_level: str = "INFO"
    log_json: bool | None = None
    health_check_timeout_seconds: float = 2.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def is_local(self) -> bool:
        return self.app_env.lower() in {"local", "dev", "development"}

    @property
    def use_json_logs(self) -> bool:
        return self.log_json if self.log_json is not None else not self.is_local


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
