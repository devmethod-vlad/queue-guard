from dishka import Provider, from_context, Scope, provide

from app.common.storages.interfaces import KeyValueStorageProtocol
from app.common.storages.redis import RedisStorage
from app.infrastructure.adapters.interfaces import ILLMQueue, IRedisSemaphore
from app.infrastructure.adapters.queue import LLMQueue
from app.infrastructure.adapters.semaphore import RedisSemaphore
from app.services.infrastructure import IHybridSearchService
from app.services.search_service import HybridSearchService
from app.settings.config import Settings, AppSettings


class ApplicationProvider(Provider):
    """Провайдер зависимостей."""

    settings = from_context(Settings, scope=Scope.APP)
    app_config = from_context(provides=AppSettings, scope=Scope.APP)

    redis_storage = provide(RedisStorage, scope=Scope.APP, provides=KeyValueStorageProtocol)
    redis_semaphore = provide(RedisSemaphore, scope=Scope.APP, provides=IRedisSemaphore)
    queue = provide(LLMQueue, scope=Scope.APP, provides=ILLMQueue)
    search_service = provide(HybridSearchService, scope=Scope.REQUEST, provides=IHybridSearchService)