from dishka import make_async_container
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI

from app.api.routers.test import router
from app.infrastructure.ioc import ApplicationProvider
from app.infrastructure.providers import RedisProvider
from app.settings.config import settings, AppSettings, Settings, RedisSettings


def create_app() -> FastAPI:
    """Инициализация приложения"""
    application = FastAPI(title="AI Search", root_path=settings.app.prefix)
    container = make_async_container(
        ApplicationProvider(),
        FastapiProvider(),
        RedisProvider(),
        context={
            AppSettings: settings.app,
            Settings: settings,
            RedisSettings: settings.redis,
        },
    )
    application.include_router(router)
    setup_dishka(container, application)
    return application

app = create_app()