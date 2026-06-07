from __future__ import annotations
from datetime import datetime, timezone

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Measurement


async def get_measurement_for_user(session: AsyncSession, tg_id: int, m_id: int) -> Measurement | None:
    user_res = await session.execute(select(User).where(User.tg_id == tg_id))
    user = user_res.scalar_one_or_none()
    if not user:
        return None

    res = await session.execute(
        select(Measurement).where(Measurement.id == m_id, Measurement.user_id == user.id)
    )
    return res.scalar_one_or_none()


async def delete_measurement_for_user(session: AsyncSession, tg_id: int, m_id: int) -> bool:
    m = await get_measurement_for_user(session, tg_id, m_id)
    if not m:
        return False

    await session.delete(m)
    await session.commit()
    return True


async def update_measurement_for_user(
    session: AsyncSession,
    tg_id: int,
    m_id: int,
    *,
    value_num: float | None = None,
    systolic: int | None = None,
    diastolic: int | None = None,
    unit: str | None = None,
    note: str | None = None,
    measured_at: datetime | None = None,
) -> bool:
    m = await get_measurement_for_user(session, tg_id, m_id)
    if not m:
        return False

    m.value_num = value_num
    m.systolic = systolic
    m.diastolic = diastolic
    m.unit = unit
    m.note = note
    if measured_at is not None:
        m.measured_at = measured_at

    await session.commit()
    return True