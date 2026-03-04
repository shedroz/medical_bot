from __future__ import annotations

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Measurement


async def _get_user_id(session: AsyncSession, tg_id: int) -> int | None:
    res = await session.execute(select(User.id).where(User.tg_id == tg_id))
    return res.scalar_one_or_none()


async def get_line_points(
    session: AsyncSession,
    tg_id: int,
    m_type: str,  # "temperature" | "pulse"
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[tuple[datetime, float]]:
    user_id = await _get_user_id(session, tg_id)
    if not user_id:
        return []

    q = (
        select(Measurement.measured_at, Measurement.value_num)
        .where(Measurement.user_id == user_id)
        .where(Measurement.type == m_type)
    )
    if date_from is not None:
        q = q.where(Measurement.measured_at >= date_from)
    if date_to is not None:
        q = q.where(Measurement.measured_at < date_to)

    q = q.order_by(Measurement.measured_at.asc())

    res = await session.execute(q)
    rows = res.all()

    points: list[tuple[datetime, float]] = []
    for dt, val in rows:
        if val is None:
            continue
        points.append((dt, float(val)))
    return points


async def get_pressure_points(
    session: AsyncSession,
    tg_id: int,
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[tuple[datetime, int, int]]:
    user_id = await _get_user_id(session, tg_id)
    if not user_id:
        return []

    q = (
        select(Measurement.measured_at, Measurement.systolic, Measurement.diastolic)
        .where(Measurement.user_id == user_id)
        .where(Measurement.type == "pressure")
    )
    if date_from is not None:
        q = q.where(Measurement.measured_at >= date_from)
    if date_to is not None:
        q = q.where(Measurement.measured_at < date_to)

    q = q.order_by(Measurement.measured_at.asc())

    res = await session.execute(q)
    rows = res.all()

    points: list[tuple[datetime, int, int]] = []
    for dt, sys, dia in rows:
        if sys is None or dia is None:
            continue
        points.append((dt, int(sys), int(dia)))
    return points