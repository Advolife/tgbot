import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import load_config
from app.db import engine as db_engine
from app.handlers.quiz import router as quiz_router
from app.services.bot_ctx import set_bot
from app.services.scheduler import init_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
log = logging.getLogger("bot")


async def main() -> None:
    cfg = load_config()
    db_engine.init_engine(cfg.database_url)
    await db_engine.create_all()
    log.info("База данных готова")

    bot = Bot(
        token=cfg.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    set_bot(bot)

    dp = Dispatcher(storage=MemoryStorage())
    dp["cfg"] = cfg
    dp.include_router(quiz_router)

    scheduler = init_scheduler(cfg.database_url)
    scheduler.start()
    log.info("Планировщик запущен")

    await bot.delete_webhook(drop_pending_updates=False)
    log.info("Бот стартует…")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await db_engine.dispose()
        log.info("Бот остановлен")


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())
