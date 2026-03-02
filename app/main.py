import asyncio
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from app.bot.reminder_worker import reminder_worker

from app.bot.routers import setup_routers

load_dotenv()


async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set in .env")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(setup_routers())

    task = asyncio.create_task(reminder_worker(bot))
    try:
        await dp.start_polling(bot)
    finally:
        task.cancel()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())