from __future__ import annotations

from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext

from app.db.session import SessionMaker
from app.db.stats_repo import get_line_points, get_pressure_points
from app.utils.plotting import plot_line, plot_pressure, LOCAL_TZ
from .keyboards import stats_menu_kb, stats_period_kb, main_menu_kb, back_kb
from .states import Stats

router = Router()


def _period_to_range(period: str) -> tuple[datetime | None, datetime | None]:
    now_local = datetime.now(LOCAL_TZ)
    if period == "7d":
        return (now_local - timedelta(days=7)).astimezone(timezone.utc), None
    if period == "30d":
        return (now_local - timedelta(days=30)).astimezone(timezone.utc), None
    return None, None


def _parse_user_range(text: str) -> tuple[datetime, datetime]:
    # принимает: YYYY-MM-DD или YYYY-MM-DD YYYY-MM-DD
    parts = text.strip().split()
    if len(parts) == 1:
        d1 = datetime.fromisoformat(parts[0]).date()
        d2 = d1
    elif len(parts) == 2:
        d1 = datetime.fromisoformat(parts[0]).date()
        d2 = datetime.fromisoformat(parts[1]).date()
        if d2 < d1:
            d1, d2 = d2, d1
    else:
        raise ValueError

    start_local = datetime(d1.year, d1.month, d1.day, tzinfo=LOCAL_TZ)
    end_local = datetime(d2.year, d2.month, d2.day, tzinfo=LOCAL_TZ) + timedelta(days=1)

    # в БД у нас UTC → фильтры тоже переводим в UTC
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


@router.message(F.text.contains("Статистика"))
async def stats_open(message: Message):
    await message.answer("📈 Выбери показатель:", reply_markup=stats_menu_kb())


@router.callback_query(F.data == "stats:back")
async def stats_back(call: CallbackQuery):
    await call.message.edit_text("📈 Выбери показатель:", reply_markup=stats_menu_kb())
    await call.answer()


@router.callback_query(F.data.startswith("stats:metric:"))
async def stats_choose_metric(call: CallbackQuery):
    metric = call.data.split(":")[-1]  # temperature/pulse/pressure
    await call.message.edit_text("Выбери период:", reply_markup=stats_period_kb(metric))
    await call.answer()


@router.callback_query(F.data.startswith("stats:period:"))
async def stats_choose_period(call: CallbackQuery, state: FSMContext):
    _, _, metric, period = call.data.split(":", 3)

    if period == "range":
        await state.set_state(Stats.entering_range)
        await state.update_data(metric=metric)
        await call.message.answer(
            "Введи период:\n"
            "• одна дата: <b>YYYY-MM-DD</b>\n"
            "• или диапазон: <b>YYYY-MM-DD YYYY-MM-DD</b>\n"
            "Пример: <b>2026-03-01 2026-03-07</b>\n\n"
            "Можно написать <b>отмена</b>.\n"
            "Для возврата — кнопка <b>⬅️ Назад</b>.",
            reply_markup=back_kb(),
        )
        await call.answer()
        return

    date_from, date_to = _period_to_range(period)
    await _send_plot(call, metric, date_from, date_to)
    await call.answer()


@router.message(Stats.entering_range)
async def stats_enter_range(message: Message, state: FSMContext):
    txt = (message.text or "").strip().lower()
    if txt in ("отмена", "cancel", "стоп", "stop"):
        await state.clear()
        await message.answer("Ок ✅ Отменено.", reply_markup=main_menu_kb())
        return

    data = await state.get_data()
    metric = data.get("metric")
    if not metric:
        await state.clear()
        await message.answer("Что-то пошло не так. Открой 📈 Статистика заново.", reply_markup=main_menu_kb())
        return

    try:
        date_from, date_to = _parse_user_range(message.text or "")
    except ValueError:
        await message.answer("Формат неверный. Введи <b>YYYY-MM-DD</b> или <b>YYYY-MM-DD YYYY-MM-DD</b>.")
        return

    await state.clear()
    # тут отправляем как обычному message (не callback)
    await _send_plot(message, metric, date_from, date_to)


async def _send_plot(target: Message | CallbackQuery, metric: str, date_from: datetime | None, date_to: datetime | None):
    tg_id = target.from_user.id if isinstance(target, CallbackQuery) else target.from_user.id

    async with SessionMaker() as session:
        if metric in ("temperature", "pulse"):
            points = await get_line_points(session, tg_id, metric, date_from, date_to)
            if metric == "temperature":
                buf = plot_line(points, "Температура", "°C")
                filename = "temperature.png"
                caption = "📈 Температура"
            else:
                buf = plot_line(points, "Пульс", "уд/мин")
                filename = "pulse.png"
                caption = "📈 Пульс"
        else:
            points = await get_pressure_points(session, tg_id, date_from, date_to)
            buf = plot_pressure(points)
            filename = "pressure.png"
            caption = "📈 Давление (SYS/DIA)"

    photo = BufferedInputFile(buf.getvalue(), filename=filename)

    if isinstance(target, CallbackQuery):
        await target.message.answer_photo(photo=photo, caption=caption)
    else:
        await target.answer_photo(photo=photo, caption=caption)