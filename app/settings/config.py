from typing import Self

from pydantic import RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvBaseSettings(BaseSettings):
    """Базовый класс для прокидывания настроек из env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AppSettings(EnvBaseSettings):
    """Настройки приложения FastAPI."""

    mode: str = "dev"
    host: str
    port: int
    debug_host: str
    debug_port: int
    workers_num: int
    access_key: str
    prefix: str = ""

    logs_host_path: str
    logs_contr_path: str

    model_name: str

    model_config = SettingsConfigDict(env_prefix="app_")


class RedisSettings(EnvBaseSettings):
    """Настройки Redis"""

    hostname: str
    port: int
    database: int
    dsn: RedisDsn | str | None = None

    @model_validator(mode="after")
    def assemble_redis_connection(self) -> Self:
        """Сборка Redis DSN"""
        if self.dsn is None:
            self.dsn = str(
                RedisDsn.build(
                    scheme="redis", host=self.hostname, port=self.port, path=f"/{self.database}"
                )
            )
        return self

    model_config = SettingsConfigDict(env_prefix="redis_")

class LLMQueueSettings(EnvBaseSettings):
    """Настройки очереди вне семафора"""

    queue_list_key: str = "llm:queue:list"
    ticket_hash_prefix: str = "llm:ticket:"
    max_size: int = 7
    ticket_ttl: int = 3600
    drain_interval_sec: int = 1
    processing_list_key: str | None = None  # список «в обработке»

    model_config = SettingsConfigDict(env_prefix="llm_queue_")

class LLMGlobalSemaphoreSettings(EnvBaseSettings):
    """Настройки глобального семафора"""

    key: str = "llm:{global}:sem"
    limit: int = 2
    ttl_ms: int = 120000
    wait_timeout_ms: int = 30000
    heartbeat_ms: int = 30000

    model_config = SettingsConfigDict(env_prefix="llm_global_sem_")



class Settings(EnvBaseSettings):
    """Настройки проекта."""

    app: AppSettings = AppSettings()
    redis: RedisSettings = RedisSettings()
    llm_queue: LLMQueueSettings = LLMQueueSettings()
    llm_global_sem: LLMGlobalSemaphoreSettings = LLMGlobalSemaphoreSettings()


settings = Settings()