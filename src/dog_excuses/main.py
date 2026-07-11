import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from dog_excuses.bot.router import create_router
from dog_excuses.catalog import validate_catalog
from dog_excuses.config import get_settings
from dog_excuses.db.session import create_engine_and_factory


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    validate_catalog()
    engine, factory = create_engine_and_factory(settings.database_url)
    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await bot.get_me()
    if not me.username:
        raise RuntimeError("Telegram bot must have a username")
    dispatcher = Dispatcher()
    dispatcher.include_router(
        create_router(factory, settings.user_hash_secret.get_secret_value(), me.username)
    )
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="excuse", description="Придумать отмазку"),
            BotCommand(command="help", description="Как это работает"),
            BotCommand(command="privacy", description="Конфиденциальность"),
        ]
    )
    ready_file = Path("/tmp/pesdnyak-ready")
    ready_file.touch()
    try:
        await dispatcher.start_polling(bot)
    finally:
        ready_file.unlink(missing_ok=True)
        await bot.session.close()
        await engine.dispose()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
