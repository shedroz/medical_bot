from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db.repo import get_or_create_user
from app.db.session import SessionMaker
from .keyboards import main_menu_kb

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    tg_id = message.from_user.id

    async with SessionMaker() as session:
        await get_or_create_user(session, tg_id)

    await message.answer(
        "Привет! Я бот для учета личных медицинских показателей.\n"
        "Выбери действие в меню ниже 👇",
        reply_markup=main_menu_kb(),
    )


# чтобы меню показывалось и по кнопке "Назад/Меню"
@router.message(F.text.lower().in_(["меню", "main menu"]))
async def menu_handler(message: Message):
    await message.answer("Главное меню 👇", reply_markup=main_menu_kb())