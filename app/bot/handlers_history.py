from __future__ import annotations

from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.db.session import SessionMaker
from app.db.repo import list_measurements
from .keyboards import history_filter_kb, history_page_kb, main_menu_kb, back_kb
from .states import History
from aiogram.exceptions import TelegramBadRequest
router = Router()

LOCAL_TZ = datetime.now().astimezone().tzinfo
PAGE_SIZE = 10

LABELS = {
    "pressure": ("Давление", None),
    "pulse": ("Пульс", "уд/мин"),
    "temperature": ("Температура", "°C"),
    "weight": ("Вес", "кг"),
    "spo2": ("SpO₂", "%"),
    "glucose": ("Глюкоза", "ммоль/л"),
    "sleep": ("Сон", "ч"),
    "wellbeing": ("Самочувствие", "балл"),
} 

# flt (строка) будем кодировать так:
# "all" | "today" | "7d" | "range:YYYY-MM-DD:YYYY-MM-DD"
def _parse_filter(flt: str) -> tuple[datetime | None, datetime | None]:
    now = datetime.now(LOCAL_TZ)

    if flt == "all":
        return None, None

    if flt == "today":
        start_local = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

    if flt == "7d":
        start_local = now - timedelta(days=7)
        return start_local.astimezone(timezone.utc), None

    if flt.startswith("range:"):
        _, a, b = flt.split(":")
        d1 = datetime.fromisoformat(a).date()
        d2 = datetime.fromisoformat(b).date()
        start_local = datetime(d1.year, d1.month, d1.day, tzinfo=LOCAL_TZ)
        end_local = datetime(d2.year, d2.month, d2.day, tzinfo=LOCAL_TZ) + timedelta(days=1)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

    return None, None

def _format_measurements(rows):
    lines = []

    for m in rows:
        label, default_unit = LABELS.get(m.type, (m.type, ""))

        # переводим время в локальное
        dt = m.measured_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        dt_str = dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")

        # давление
        if m.type == "pressure":
            if m.systolic is not None and m.diastolic is not None:
                value = f"{m.systolic}/{m.diastolic}"
            else:
                value = "-"

        # остальные показатели
        else:
            if m.value_num is None:
                value = "-"
            else:
                unit = m.unit if m.unit else default_unit
                value = f"{m.value_num:g} {unit}".strip()

        lines.append(f"{dt_str} — {label}: {value}")

    return "\n".join(lines)


async def _send_history(target: Message | CallbackQuery, tg_id: int, page: int, flt: str):
    offset = page * PAGE_SIZE
    date_from, date_to = _parse_filter(flt)

    async with SessionMaker() as session:
        items, total = await list_measurements(
            session=session,
            tg_id=tg_id,
            limit=PAGE_SIZE,
            offset=offset,
            date_from=date_from,
            date_to=date_to,
        )

    text = _format_measurements(items)
    if not items:
        text = "Пока нет записей 📭\n\nНажми «➕ Добавить показатель», чтобы добавить первую."
    kb = history_page_kb(page=page, total=total, page_size=PAGE_SIZE, flt=flt)

    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest as e:
            print("EDIT_TEXT ERROR:", str(e))
            # fallback: отправим новым сообщением
            await target.message.answer(text, reply_markup=kb)
        await target.answer()
    else:
        try:
            await target.answer(text, reply_markup=kb)
        except TelegramBadRequest as e:
            print("ANSWER ERROR:", str(e))
            await target.answer("Не смогла показать историю (ошибка Telegram).", reply_markup=main_menu_kb())


@router.message(F.text.contains("История"))
async def history_open(message: Message):
    await _send_history(message, tg_id=message.from_user.id, page=0, flt="all")


@router.callback_query(F.data == "hist:open_filters")
async def history_filters(call: CallbackQuery):
    await call.message.edit_text("Выбери фильтр:", reply_markup=history_filter_kb())
    await call.answer()


@router.callback_query(F.data.startswith("hist:filter:"))
async def history_apply_filter(call: CallbackQuery, state: FSMContext):
    flt_key = call.data.split(":")[-1]

    if flt_key == "range":
        await state.set_state(History.entering_range)
        await call.message.answer(
            "Введи период:\n"
            "• одна дата: <b>YYYY-MM-DD</b>\n"
            "• или диапазон: <b>YYYY-MM-DD YYYY-MM-DD</b>\n"
            "Пример: <b>2026-03-01 2026-03-07</b>\n\n"
            "Можно написать <b>отмена</b>.",
            reply_markup=back_kb(),
        )
        await call.answer()
        return

    # today / 7d / all
    await _send_history(call, tg_id=call.from_user.id, page=0, flt=flt_key)


@router.callback_query(F.data.startswith("hist:page:"))
async def history_page(call: CallbackQuery):
    _, _, page_str, flt = call.data.split(":", 3)
    page = max(int(page_str), 0)
    await _send_history(call, tg_id=call.from_user.id, page=page, flt=flt)


@router.callback_query(F.data == "hist:noop")
async def hist_noop(call: CallbackQuery):
    await call.answer()


@router.message(History.entering_range)
async def history_range_enter(message: Message, state: FSMContext):
    text = (message.text or "").strip().lower()
    if text in ("отмена", "cancel"):
        await state.clear()
        await message.answer("Ок, вернулась в меню 👇", reply_markup=main_menu_kb())
        return

    parts = text.split()
    try:
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
    except ValueError:
        await message.answer("Не поняла формат. Введи <b>YYYY-MM-DD</b> или <b>YYYY-MM-DD YYYY-MM-DD</b>.")
        return

    flt = f"range:{d1.isoformat()}:{d2.isoformat()}"
    await state.clear()
    await _send_history(message, tg_id=message.from_user.id, page=0, flt=flt)