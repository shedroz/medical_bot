from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Measurement


async def get_or_create_user(session: AsyncSession, tg_id: int) -> User:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(tg_id=tg_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


async def add_measurement(
    session,
    tg_id: int,
    m_type: str,
    value_num: float | None = None,
    systolic: int | None = None,
    diastolic: int | None = None,
    measured_at: datetime | None = None,
):
    user = await get_or_create_user(session, tg_id)

    measurement = Measurement(
        user_id=user.id,
        type=m_type,
        value_num=value_num,
        systolic=systolic,
        diastolic=diastolic,
        measured_at=measured_at or datetime.now(timezone.utc),
    )
    session.add(measurement)
    await session.commit()
    await session.refresh(measurement)
    return measurement

async def list_measurements(
    session: AsyncSession,
    tg_id: int,
    limit: int = 10,
    offset: int = 0,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[Measurement], int]:
    # получаем user
    user_res = await session.execute(select(User).where(User.tg_id == tg_id))
    user = user_res.scalar_one_or_none()
    if user is None:
        return [], 0

    # базовый запрос
    q = select(Measurement).where(Measurement.user_id == user.id)
    cq = select(func.count()).select_from(Measurement).where(Measurement.user_id == user.id)

    # фильтр по датам
    if date_from is not None:
        q = q.where(Measurement.measured_at >= date_from)
        cq = cq.where(Measurement.measured_at >= date_from)
    if date_to is not None:
        q = q.where(Measurement.measured_at < date_to)  # date_to как "исключая верхнюю границу"
        cq = cq.where(Measurement.measured_at < date_to)

    q = q.order_by(Measurement.measured_at.desc()).limit(limit).offset(offset)

    items_res = await session.execute(q)
    items = items_res.scalars().all()

    total_res = await session.execute(cq)
    total = int(total_res.scalar() or 0)

    return items, total