from __future__ import annotations

from datetime import datetime, time, timezone
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Reminder, User


async def ensure_user(session: AsyncSession, tg_id: int) -> User:
    res = await session.execute(select(User).where(User.tg_id == tg_id))
    user = res.scalar_one_or_none()
    if user is None:
        user = User(tg_id=tg_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def list_reminders(session: AsyncSession, tg_id: int) -> list[Reminder]:
    user = await ensure_user(session, tg_id)
    res = await session.execute(
        select(Reminder).where(Reminder.user_id == user.id).order_by(Reminder.time.asc())
    )
    return list(res.scalars().all())


async def add_reminder(session: AsyncSession, tg_id: int, t: time) -> Reminder:
    user = await ensure_user(session, tg_id)
    r = Reminder(user_id=user.id, time=t, enabled=True)
    session.add(r)
    await session.commit()
    await session.refresh(r)
    return r


async def toggle_reminder(session: AsyncSession, tg_id: int, reminder_id: int) -> None:
    user = await ensure_user(session, tg_id)
    res = await session.execute(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user.id)
    )
    r = res.scalar_one_or_none()
    if not r:
        return
    r.enabled = not r.enabled
    await session.commit()


async def delete_reminder(session: AsyncSession, tg_id: int, reminder_id: int) -> None:
    user = await ensure_user(session, tg_id)
    await session.execute(
        delete(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user.id)
    )
    await session.commit()


async def due_reminders(session: AsyncSession, now_local: datetime) -> list[tuple[int, int, time]]:
    hh = now_local.hour
    mm = now_local.minute

    target_time = time(hour=hh, minute=mm) 

    start_today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    q = (
        select(User.tg_id, Reminder.id, Reminder.time)
        .join(Reminder, Reminder.user_id == User.id)
        .where(Reminder.enabled.is_(True))
        .where(Reminder.time == target_time) 
        .where((Reminder.last_sent_at.is_(None)) | (Reminder.last_sent_at < start_today))
    )

    res = await session.execute(q)
    return list(res.all())


async def mark_sent(session: AsyncSession, reminder_id: int, sent_at_local: datetime) -> None:
    await session.execute(
        update(Reminder)
        .where(Reminder.id == reminder_id)
        .values(last_sent_at=sent_at_local)
    )
    await session.commit()