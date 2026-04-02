import asyncio
from aiogram import Bot

from collector.config import settings
from collector.engine import ensure_db_initialized
from collector.saver import raw_msgs_to_db
from collector.logger import logger


async def run_bot():
    await ensure_db_initialized()
    bot = Bot(token=settings.BOT_TOKEN)
    logger.info("Коллектор запущен")

    try:
        while True:
            await raw_msgs_to_db(bot)
            await asyncio.sleep(30)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_bot())