import re
from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.db.session import SessionMaker
from app.db.reminders_repo import list_reminders, add_reminder, toggle_reminder, delete_reminder
from .keyboards import main_menu_kb, reminders_menu_kb, reminders_list_kb, back_kb, confirm_reminder_delete_kb
from .states import Reminders

router = Router()

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")  # HH:MM


async def _show_list(call_or_msg, tg_id: int):
    async with SessionMaker() as session:
        items = await list_reminders(session, tg_id)

    text = "<b>Напоминания</b>\n"
    text += "Нажми на время, чтобы включить/выключить. Корзина — удалить.\n\n"
    text += ("Список пуст.\n" if not items else "Ваши напоминания:\n")

    kb = reminders_list_kb(items) if items else reminders_menu_kb()

    if isinstance(call_or_msg, CallbackQuery):
        await call_or_msg.message.edit_text(text, reply_markup=kb)
        await call_or_msg.answer()
    else:
        await call_or_msg.answer(text, reply_markup=kb)


@router.message(F.text.contains("Напоминания"))
async def reminders_open(message: Message):
    await _show_list(message, message.from_user.id)


@router.callback_query(F.data == "rem:list")
async def reminders_list(call: CallbackQuery):
    await _show_list(call, call.from_user.id)


@router.callback_query(F.data == "rem:add")
async def reminders_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(Reminders.entering_time)
    await call.message.answer(
        "Введи время напоминания в формате <b>HH:MM</b> (например 09:00).\n"
        "Можно написать <b>отмена</b>.",
        reply_markup=back_kb(),
    )
    await call.answer()


@router.message(Reminders.entering_time)
async def reminders_enter_time(message: Message, state: FSMContext):
    txt = (message.text or "").strip().lower()
    if txt in ("отмена", "cancel"):
        await state.clear()
        await message.answer("Ок, вернулась в меню 👇", reply_markup=main_menu_kb())
        return

    m = TIME_RE.match(txt)
    if not m:
        await message.answer("Формат неверный. Пример: <b>09:00</b>. Попробуй ещё раз:")
        return

    hh = int(m.group(1))
    mm = int(m.group(2))

    from datetime import time
    t = time(hour=hh, minute=mm)

    async with SessionMaker() as session:
        await add_reminder(session, message.from_user.id, t)

    await state.clear()
    await message.answer("✅ Напоминание добавлено.")
    await _show_list(message, message.from_user.id)


@router.callback_query(F.data.startswith("rem:toggle:"))
async def reminders_toggle(call: CallbackQuery):
    reminder_id = int(call.data.split(":")[-1])
    async with SessionMaker() as session:
        await toggle_reminder(session, call.from_user.id, reminder_id)
    await _show_list(call, call.from_user.id)


@router.callback_query(F.data.startswith("rem:del:"))
async def reminder_delete_confirm(call: CallbackQuery):
    reminder_id = int(call.data.split(":")[2])

    await call.message.answer(
        "❓ Точно удалить это напоминание?",
        reply_markup=confirm_reminder_delete_kb(reminder_id)
    )

    await call.answer()

@router.callback_query(F.data.startswith("rem:del_yes:"))
async def reminder_delete_yes(call: CallbackQuery):
    reminder_id = int(call.data.split(":")[2])

    async with SessionMaker() as session:
        await delete_reminder(session, call.from_user.id, reminder_id)

    await call.answer("Удалено ✅")

    try:
        await call.message.delete()
    except Exception:
        pass

    await call.message.answer(
        "✅ Напоминание удалено",
        reply_markup=main_menu_kb()
    )

    await _show_list(call.message, call.from_user.id)

@router.callback_query(F.data == "rem:del_no")
async def reminder_delete_no(call: CallbackQuery):
    await call.answer("Удаление отменено")

    try:
        await call.message.delete()
    except Exception:
        pass

    await call.message.answer(
        "Удаление отменено.",
        reply_markup=main_menu_kb()
    )

    await _show_list(call.message, call.from_user.id)