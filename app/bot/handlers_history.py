from __future__ import annotations

from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.db.session import SessionMaker
from app.db.repo import list_measurements
from .keyboards import history_filter_kb, history_page_kb, main_menu_kb, back_kb, confirm_delete_kb, edit_cancel_kb
from .states import History
from aiogram.exceptions import TelegramBadRequest

import re
from app.db.measurements_repo import get_measurement_for_user, delete_measurement_for_user, update_measurement_for_user
from .states import EditMeasurement
import os
from zoneinfo import ZoneInfo


router = Router()

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Europe/Moscow")
LOCAL_TZ = ZoneInfo(APP_TIMEZONE)

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

PRESSURE_RE = re.compile(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$")

METRICS = {
    "pulse": {"label": "Пульс", "unit": "уд/мин", "min": 30, "max": 220, "kind": "int"},
    "temperature": {"label": "Температура", "unit": "°C", "min": 34.0, "max": 43.0, "kind": "float"},
    "weight": {"label": "Вес", "unit": "кг", "min": 20.0, "max": 300.0, "kind": "float"},
    "spo2": {"label": "SpO₂", "unit": "%", "min": 50, "max": 100, "kind": "int"},
    "glucose": {"label": "Глюкоза", "unit": "ммоль/л", "min": 1.0, "max": 40.0, "kind": "float"},
    "sleep": {"label": "Сон", "unit": "ч", "min": 0.0, "max": 24.0, "kind": "float"},
    "wellbeing": {"label": "Самочувствие", "unit": "балл", "min": 1, "max": 10, "kind": "int"},
}

ICONS = {
    "pressure": "🩸",
    "pulse": "❤️",
    "temperature": "🌡",
    "weight": "⚖️",
    "spo2": "🫁",
    "glucose": "🍬",
    "sleep": "😴",
    "wellbeing": "😌",
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

def _format_one_value(m) -> str:
    label, default_unit = LABELS.get(m.type, (m.type, ""))

    if m.type == "pressure":
        val = f"{m.systolic}/{m.diastolic}" if m.systolic is not None and m.diastolic is not None else "-"
    else:
        if m.value_num is None:
            val = "-"
        else:
            unit = m.unit if m.unit else default_unit
            val = f"{m.value_num:g} {unit}".strip()

    return f"{label}: {val}"

def _format_measurements(rows):
    if not rows:
        return (
            "📖 <b>История измерений</b>\n\n"
            "Пока нет записей 📭\n\n"
            "Нажми «➕ Добавить показатель», чтобы добавить первую."
        )

    lines = ["📖 <b>История измерений</b>\n"]

    last_day = None

    for i, m in enumerate(rows, start=1):
        label, default_unit = LABELS.get(m.type, (m.type, ""))
        icon = ICONS.get(m.type, "📊")

        dt = m.measured_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        dt_local = dt.astimezone(LOCAL_TZ)
        day_key = dt_local.date()

        # Заголовок дня
        if last_day != day_key:
            lines.append(f"\n📅 <b>{dt_local.strftime('%d.%m.%Y')}</b>")
            last_day = day_key

        time_str = dt_local.strftime("%H:%M")

        # значение
        if m.type == "pressure":
            value = (
                f"{m.systolic}/{m.diastolic}"
                if (m.systolic is not None and m.diastolic is not None)
                else "-"
            )
        else:
            if m.value_num is None:
                value = "-"
            else:
                unit = m.unit if m.unit else default_unit
                value = f"{m.value_num:g} {unit}".strip()

        # 1 строка на запись (очень читаемо)
        lines.append(f"<b>{i})</b> {time_str}  {icon} <b>{label}</b>: {value}")

    return "\n".join(lines).strip()


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
    kb = history_page_kb(page=page, total=total, page_size=PAGE_SIZE, flt=flt, items=items)

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


@router.callback_query(F.data.startswith("hist:del:"))
async def hist_delete_ask(call: CallbackQuery):
    _, _, mid, page, flt = call.data.split(":", 4)
    mid = int(mid)

    await call.message.answer(
        "Точно удалить эту запись? 🗑",
        reply_markup=confirm_delete_kb(mid=mid, page=int(page), flt=flt),
    )
    await call.answer()

@router.callback_query(F.data.startswith("hist:del_yes:"))
async def hist_delete_yes(call: CallbackQuery):
    _, _, mid, page, flt = call.data.split(":", 4)
    mid = int(mid)

    async with SessionMaker() as session:
        ok = await delete_measurement_for_user(session, call.from_user.id, mid)

    await call.answer("Удалено ✅" if ok else "Не найдено")

    # удалим сообщение с подтверждением (по желанию)
    try:
        await call.message.delete()
    except Exception:
        pass

    # обновим историю
    await _send_history(call, tg_id=call.from_user.id, page=int(page), flt=flt)

@router.callback_query(F.data.startswith("hist:del_no:"))
async def hist_delete_no(call: CallbackQuery):
    _, _, page, flt = call.data.split(":", 3)
    await call.answer("Ок, не удаляю")
    try:
        await call.message.delete()
    except Exception:
        pass
    await _send_history(call, tg_id=call.from_user.id, page=int(page), flt=flt)

@router.callback_query(F.data.startswith("hist:edit:"))
async def hist_edit_start(call: CallbackQuery, state: FSMContext):
    _, _, mid, page, flt = call.data.split(":", 4)
    mid = int(mid)

    async with SessionMaker() as session:
        m = await get_measurement_for_user(session, call.from_user.id, mid)

    if not m:
        await call.answer("Запись не найдена")
        return

    await state.set_state(EditMeasurement.entering_value)
    await state.update_data(mid=mid, page=int(page), flt=flt, m_type=m.type)

    old_value = _format_one_value(m)  # <-- функция форматирования одной записи (должна быть в файле)

    if m.type == "pressure":
        prompt = (
            "✏️ <b>Редактирование</b>\n"
            f"Сейчас: <b>{old_value}</b>\n\n"
            "Введи новое давление в формате <b>120/80</b>:"
        )
    else:
        cfg = METRICS.get(m.type, {"label": m.type, "unit": ""})
        prompt = (
            "✏️ <b>Редактирование</b>\n"
            f"Сейчас: <b>{old_value}</b>\n\n"
            f"Введи новое значение для <b>{cfg['label']}</b> ({cfg['unit']}):"
        )

    await call.message.answer("Отмена:", reply_markup=edit_cancel_kb())
    await call.answer()

@router.message(EditMeasurement.entering_value)
async def hist_edit_enter_value(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    low = txt.lower()

    if low in ("отмена", "cancel", "стоп", "stop"):
        await state.clear()
        await message.answer("Ок ✅ Отменено.", reply_markup=main_menu_kb())
        return

    data = await state.get_data()
    mid = data.get("mid")
    m_type = data.get("m_type")
    page = data.get("page", 0)
    flt = data.get("flt", "all")

    if not mid or not m_type:
        await state.clear()
        await message.answer("Что-то пошло не так. Открой историю заново.", reply_markup=main_menu_kb())
        return

    value_num = None
    systolic = None
    diastolic = None
    unit = None

    if m_type == "pressure":
        m = PRESSURE_RE.match(txt)
        if not m:
            await message.answer("Неверный формат. Пример: <b>120/80</b>. Попробуй ещё раз:")
            return
        sys = int(m.group(1)); dia = int(m.group(2))
        if not (50 <= sys <= 250 and 30 <= dia <= 150 and sys > dia):
            await message.answer("Значения выглядят странно. Пример: <b>120/80</b>. Попробуй ещё раз:")
            return
        systolic, diastolic = sys, dia
    else:
        cfg = METRICS.get(m_type)
        if not cfg:
            await message.answer("Неизвестный показатель. Отмени и попробуй заново.")
            return

        raw = txt.replace(",", ".")
        try:
            val = float(raw)
        except ValueError:
            await message.answer(f"{cfg['label']} должно быть числом. Попробуй ещё раз:")
            return

        if cfg["kind"] == "int":
            if abs(val - round(val)) > 1e-9:
                await message.answer(f"{cfg['label']} должно быть целым числом. Попробуй ещё раз:")
                return
            v = int(round(val))
            if not (cfg["min"] <= v <= cfg["max"]):
                await message.answer(f"{cfg['label']} вне диапазона {cfg['min']}–{cfg['max']}. Попробуй ещё раз:")
                return
            value_num = float(v)
        else:
            if not (cfg["min"] <= val <= cfg["max"]):
                await message.answer(f"{cfg['label']} вне диапазона {cfg['min']}–{cfg['max']}. Попробуй ещё раз:")
                return
            value_num = float(val)

        unit = cfg["unit"]

    async with SessionMaker() as session:
        ok = await update_measurement_for_user(
            session,
            message.from_user.id,
            int(mid),
            value_num=value_num,
            systolic=systolic,
            diastolic=diastolic,
            unit=unit,
        )

    await state.clear()
    await message.answer("✅ Обновлено!", reply_markup=main_menu_kb())

    # можно автоматически показать обновлённую историю:
    # (отправляем новым сообщением)
    await _send_history(message, tg_id=message.from_user.id, page=int(page), flt=str(flt))  

@router.callback_query(F.data == "hist:edit_cancel")
async def hist_edit_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Редактирование отменено")
    try:
        await call.message.delete()
    except Exception:
        pass