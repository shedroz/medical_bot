import re
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.session import SessionMaker
from app.db.repo import add_measurement
from .keyboards import main_menu_kb, measurement_type_kb, back_kb
from .states import AddMeasurement

router = Router()

# маппинг кнопок → тип в БД
TYPE_MAP = {
    "🩸 Давление": "pressure",
    "❤️ Пульс": "pulse",
    "🌡 Температура": "temperature",
}

PRESSURE_RE = re.compile(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$")  # 120/80


@router.message(F.text.contains("Добавить показатель"))
async def add_measurement_start(message: Message, state: FSMContext):
    await state.set_state(AddMeasurement.choosing_type)
    await message.answer("Выбери показатель:", reply_markup=measurement_type_kb())


@router.message(AddMeasurement.choosing_type, F.text == "⬅️ Назад")
async def add_measurement_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню 👇", reply_markup=main_menu_kb())


@router.message(AddMeasurement.choosing_type, F.text.in_(TYPE_MAP.keys()))
async def add_measurement_choose_type(message: Message, state: FSMContext):
    m_type = TYPE_MAP[message.text]
    await state.update_data(m_type=m_type)
    await state.set_state(AddMeasurement.entering_value)

    if m_type == "pressure":
        prompt = "Введи давление в формате <b>120/80</b>:"
    elif m_type == "pulse":
        prompt = "Введи пульс (целое число, например <b>72</b>):"
    else:
        prompt = "Введи температуру (например <b>36.6</b>):"

    await message.answer(prompt, reply_markup=back_kb())


@router.message(AddMeasurement.choosing_type)
async def add_measurement_choose_type_invalid(message: Message):
    await message.answer("Выбери показатель кнопкой ниже 👇", reply_markup=measurement_type_kb())


@router.message(AddMeasurement.entering_value, F.text == "⬅️ Назад")
async def add_measurement_value_back(message: Message, state: FSMContext):
    await state.set_state(AddMeasurement.choosing_type)
    await message.answer("Выбери показатель:", reply_markup=measurement_type_kb())


@router.message(AddMeasurement.entering_value)
async def add_measurement_enter_value(message: Message, state: FSMContext):
    # безопасно получаем state-data
    data = await state.get_data()
    m_type = data.get("m_type")
    if not m_type:
        # если неожиданно нет типа — попросим начать заново
        await state.clear()
        await message.answer("Что-то пошло не так — начни ввод заново.", reply_markup=main_menu_kb())
        return

    text = (message.text or "").strip()

    # локальные переменные (чтобы не было глобалей)
    value_num = None
    systolic = None
    diastolic = None

    # валидация + парсинг
    if m_type == "pressure":
        m = PRESSURE_RE.match(text)
        if not m:
            await message.answer("Неверный формат. Пример: <b>120/80</b>. Попробуй ещё раз:")
            return
        sys = int(m.group(1))
        dia = int(m.group(2))
        # простая проверка адекватности
        if not (50 <= sys <= 250 and 30 <= dia <= 150 and sys > dia):
            await message.answer("Значения выглядят странно. Пример: <b>120/80</b>. Попробуй ещё раз:")
            return
        systolic = sys
        diastolic = dia

    elif m_type == "pulse":
        if not text.isdigit():
            await message.answer("Пульс должен быть целым числом. Пример: <b>72</b>. Попробуй ещё раз:")
            return
        pulse = int(text)
        if not (30 <= pulse <= 220):
            await message.answer("Пульс вне диапазона 30–220. Попробуй ещё раз:")
            return
        value_num = float(pulse)

    else:  # temperature
        try:
            temp = float(text.replace(",", "."))
        except ValueError:
            await message.answer("Температура должна быть числом. Пример: <b>36.6</b>. Попробуй ещё раз:")
            return
        if not (34.0 <= temp <= 43.0):
            await message.answer("Температура вне диапазона 34.0–43.0. Попробуй ещё раз:")
            return
        value_num = float(temp)

    # сохранение в БД с обработкой ошибок
    try:
        async with SessionMaker() as session:
            await add_measurement(
                session=session,
                tg_id=message.from_user.id,
                m_type=m_type,
                value_num=value_num,
                systolic=systolic if m_type == "pressure" else None,
                diastolic=diastolic if m_type == "pressure" else None,
            )
    except Exception as e:
        # лог — можно печатать или логировать в файл. Покажем пользователю понятное сообщение.
        print("DB error while saving measurement:", repr(e))
        await message.answer("Ошибка при сохранении в базу. Попробуй позже.")
        return

    await state.clear()
    await message.answer("✅ Сохранено!", reply_markup=main_menu_kb())