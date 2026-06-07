import asyncio
from datetime import datetime

from aiogram import Bot

from app.db.session import SessionMaker
from app.db.reminders_repo import due_reminders, mark_sent
import os
from zoneinfo import ZoneInfo

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Europe/Moscow")
LOCAL_TZ = ZoneInfo(APP_TIMEZONE)

async def reminder_worker(bot: Bot):
    #Каждую минуту проверяем напоминания
    while True:
        now_local = datetime.now(LOCAL_TZ).replace(second=0, microsecond=0)
        try:
            async with SessionMaker() as session:
                due = await due_reminders(session, now_local)

                for tg_id, reminder_id, _t in due:
                    try:
                        await bot.send_message(
                            tg_id,
                            "⏰ Напоминание: внеси медицинские показатели (давление/пульс/температура).",
                        )
                        await mark_sent(session, reminder_id, now_local)
                        print("[worker] sent to", tg_id, "reminder", reminder_id)  # лог отправки
                    except Exception as e:
                        print("[worker] send error:", repr(e))

        except Exception as e:
            print("[worker] db error:", repr(e))

        await asyncio.sleep(60)