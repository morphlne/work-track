import asyncio
import logging
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher

from bot.application.task_tracker_service import TaskTrackerService
from bot.config.settings import load_settings
from bot.infrastructure.database.sqlite_cache_storage import SQLiteCacheStorage
from bot.infrastructure.database.sqlite_connection import SQLiteConnectionManager
from bot.infrastructure.database.sqlite_lead_repository import SQLiteLeadRepository
from bot.infrastructure.database.sqlite_task_repository import SQLiteTaskRepository
from bot.infrastructure.database.sqlite_user_settings_repository import (
    SQLiteUserSettingsRepository,
)
from bot.infrastructure.external_api.nbrb_currency_client import NbrbCurrencyClient
from bot.infrastructure.external_api.open_meteo_client import OpenMeteoClient
from bot.infrastructure.mail.gas_dispatcher import GoogleAppsScriptEmailDispatcher
from bot.infrastructure.mail.smtp_dispatcher import SmtpEmailDispatcher
from bot.infrastructure.api.healthcheck_server import HealthcheckServer
from bot.localization.translator import Translator
from bot.presentation.handlers.tracker_handlers import build_tracker_router


async def run_bot() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = load_settings()

    translator = Translator(
        locales_dir=Path(__file__).resolve().parent / "locales",
        default_locale=settings.default_locale,
    )

    connection_manager = SQLiteConnectionManager(settings.database_path)
    task_repository = SQLiteTaskRepository(connection_manager)
    user_settings_repository = SQLiteUserSettingsRepository(connection_manager)
    lead_repository = SQLiteLeadRepository(connection_manager)
    cache_storage = SQLiteCacheStorage(connection_manager)

    await task_repository.initialize()
    await user_settings_repository.initialize()
    await lead_repository.initialize()
    await cache_storage.initialize()

    async with aiohttp.ClientSession() as http_session:
        currency_client = NbrbCurrencyClient(
            session=http_session,
            cache_storage=cache_storage,
            cache_ttl_seconds=settings.api_cache_ttl_seconds,
        )
        weather_client = OpenMeteoClient(
            session=http_session,
            cache_storage=cache_storage,
            latitude=settings.default_latitude,
            longitude=settings.default_longitude,
            city_name=settings.default_city_name,
            cache_ttl_seconds=settings.api_cache_ttl_seconds,
        )
        if settings.email_provider.strip().lower() == "gas":
            email_dispatcher = GoogleAppsScriptEmailDispatcher(
                session=http_session,
                webhook_url=settings.gas_webhook_url,
                secret_token=settings.gas_secret_token,
            )
        else:
            email_dispatcher = SmtpEmailDispatcher(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                sender_email=settings.smtp_sender_email,
            )

        tracker_service = TaskTrackerService(
            task_repository=task_repository,
            user_settings_repository=user_settings_repository,
            lead_repository=lead_repository,
            currency_provider=currency_client,
            weather_provider=weather_client,
            email_dispatcher=email_dispatcher,
            lead_recipient_email=settings.lead_recipient_email,
            translator=translator,
        )

        bot = Bot(token=settings.bot_token)
        dispatcher = Dispatcher()
        dispatcher.include_router(build_tracker_router(tracker_service, translator))

        async with HealthcheckServer(port=settings.healthcheck_port):
            await dispatcher.start_polling(bot)


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
