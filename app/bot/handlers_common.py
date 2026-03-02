from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message

from .keyboards import main_menu_kb, measurement_type_kb
from .states import AddMeasurement, History, Reminders

router = Router()

CANCEL_WORDS = {"отмена", "cancel", "стоп", "stop"}


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "<b>Помощь</b>\n\n"
        "Команды:\n"
        "• /start — запуск\n"
        "• /help — помощь\n\n"
        "Общее:\n"
        "• В любой момент напиши <b>отмена</b>, чтобы сбросить действие.\n"
        "• Кнопка <b>⬅️ Назад</b> возвращает на шаг назад.\n\n"
        "Форматы ввода:\n"
        "• Давление: <b>120/80</b>\n"
        "• Пульс: <b>72</b>\n"
        "• Температура: <b>36.6</b> (можно 36,6)\n"
        "• Период истории: <b>YYYY-MM-DD</b> или <b>YYYY-MM-DD YYYY-MM-DD</b>\n"
        "• Время напоминания: <b>HH:MM</b> (например 09:00)\n",
        reply_markup=main_menu_kb(),
    )


@router.message(F.text, F.text.lower().in_(CANCEL_WORDS))
async def cancel_anywhere(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Ок ✅ Действие отменено.", reply_markup=main_menu_kb())


@router.message(F.text == "🏠 Меню")
async def menu_button(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню 👇", reply_markup=main_menu_kb())


@router.message(F.text == "⬅️ Назад")
async def back_universal(message: Message, state: FSMContext):
    st: State | None = await state.get_state()

    if st == AddMeasurement.entering_value:
        await state.set_state(AddMeasurement.choosing_type)
        await message.answer("Выбери показатель:", reply_markup=measurement_type_kb())
        return

    if st == AddMeasurement.choosing_type:
        await state.clear()
        await message.answer("Главное меню 👇", reply_markup=main_menu_kb())
        return

    if st == History.entering_range:
        await state.clear()
        await message.answer(
            "Ок. Открой <b>📖 История</b> и выбери фильтр заново 👇",
            reply_markup=main_menu_kb(),
        )
        return

    if st == Reminders.entering_time:
        await state.clear()
        await message.answer("Ок. Возвращаюсь в меню 👇", reply_markup=main_menu_kb())
        return

    await state.clear()
    await message.answer("Главное меню 👇", reply_markup=main_menu_kb())
