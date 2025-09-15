from dishka import Provider, from_context, Scope, provide
import redis.asyncio as redis
from app.settings.config import RedisSettings


class RedisProvider(Provider):
    """Провайдер для Redis."""

    redis_settings = from_context(provides=RedisSettings, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def redis_client(self, redis_settings: RedisSettings) -> redis.Redis:
        """Получение клиента Redis."""
        dsn = str(redis_settings.dsn)
        connection = redis.from_url(dsn)  # type: ignore
        return connection.client()
