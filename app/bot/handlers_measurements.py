import re
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.session import SessionMaker
from app.db.repo import add_measurement
from .keyboards import main_menu_kb, measurement_type_kb, back_kb
from .states import AddMeasurement

router = Router()

# Кнопка -> тип в БД (ДОЛЖНО совпадать с текстом кнопок в measurement_type_kb)
TYPE_MAP = {
    "🩸 Давление": "pressure",
    "❤️ Пульс": "pulse",
    "🌡 Температура": "temperature",
    "⚖️ Вес": "weight",
    "🫁 SpO₂": "spo2",
    "🍬 Глюкоза": "glucose",
    "😴 Сон": "sleep",
    "😌 Самочувствие": "wellbeing",
}

# Настройки валидации для всех метрик, кроме давления
METRICS = {
    "pulse": {"label": "Пульс", "unit": "уд/мин", "min": 30, "max": 220, "kind": "int"},
    "temperature": {"label": "Температура", "unit": "°C", "min": 34.0, "max": 43.0, "kind": "float"},
    "weight": {"label": "Вес", "unit": "кг", "min": 20.0, "max": 300.0, "kind": "float"},
    "spo2": {"label": "SpO₂", "unit": "%", "min": 50, "max": 100, "kind": "int"},
    "glucose": {"label": "Глюкоза", "unit": "ммоль/л", "min": 1.0, "max": 40.0, "kind": "float"},
    "sleep": {"label": "Сон", "unit": "ч", "min": 0.0, "max": 24.0, "kind": "float"},
    "wellbeing": {"label": "Самочувствие", "unit": "балл", "min": 1, "max": 10, "kind": "int"},
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
    else:
        cfg = METRICS[m_type]
        # можно добавить примеры по каждому показателю, но пока универсально
        prompt = f"Введи <b>{cfg['label']}</b> ({cfg['unit']})."

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
    data = await state.get_data()
    m_type = data.get("m_type")
    if not m_type:
        await state.clear()
        await message.answer("Что-то пошло не так — начни ввод заново.", reply_markup=main_menu_kb())
        return

    text = (message.text or "").strip()

    value_num: float | None = None
    systolic: int | None = None
    diastolic: int | None = None
    unit: str | None = None
    note: str | None = None  # на будущее

    if m_type == "pressure":
        m = PRESSURE_RE.match(text)
        if not m:
            await message.answer("Неверный формат. Пример: <b>120/80</b>. Попробуй ещё раз:")
            return
        sys = int(m.group(1))
        dia = int(m.group(2))
        if not (50 <= sys <= 250 and 30 <= dia <= 150 and sys > dia):
            await message.answer("Значения выглядят странно. Пример: <b>120/80</b>. Попробуй ещё раз:")
            return
        systolic = sys
        diastolic = dia

    else:
        cfg = METRICS.get(m_type)
        if not cfg:
            await message.answer("Неизвестный показатель. Попробуй выбрать заново.", reply_markup=measurement_type_kb())
            await state.set_state(AddMeasurement.choosing_type)
            return

        raw = text.replace(",", ".")
        try:
            val = float(raw)
        except ValueError:
            await message.answer(f"{cfg['label']} должно быть числом. Попробуй ещё раз:")
            return

        if cfg["kind"] == "int":
            # запрещаем дробные значения (72.5)
            if abs(val - round(val)) > 1e-9:
                await message.answer(f"{cfg['label']} должно быть целым числом. Попробуй ещё раз:")
                return
            val_int = int(round(val))
            if not (cfg["min"] <= val_int <= cfg["max"]):
                await message.answer(f"{cfg['label']} вне диапазона {cfg['min']}–{cfg['max']}. Попробуй ещё раз:")
                return
            value_num = float(val_int)
        else:
            if not (cfg["min"] <= val <= cfg["max"]):
                await message.answer(f"{cfg['label']} вне диапазона {cfg['min']}–{cfg['max']}. Попробуй ещё раз:")
                return
            value_num = float(val)

        unit = cfg["unit"]

    try:
        async with SessionMaker() as session:
            await add_measurement(
                session=session,
                tg_id=message.from_user.id,
                m_type=m_type,
                value_num=value_num,
                systolic=systolic if m_type == "pressure" else None,
                diastolic=diastolic if m_type == "pressure" else None,
                unit=unit,
                note=note,
            )
    except Exception as e:
        print("DB error while saving measurement:", repr(e))
        await message.answer("Ошибка при сохранении в базу. Попробуй позже.")
        return

    await state.clear()
    await message.answer("✅ Сохранено!", reply_markup=main_menu_kb())