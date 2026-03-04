from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить показатель")],
            [KeyboardButton(text="📖 История"), KeyboardButton(text="⏰ Напоминания")],
            [KeyboardButton(text="📈 Статистика")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )

def measurement_type_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🩸 Давление"), KeyboardButton(text="❤️ Пульс")],
            [KeyboardButton(text="🌡 Температура"), KeyboardButton(text="⚖️ Вес")],
            [KeyboardButton(text="🫁 SpO₂"), KeyboardButton(text="🍬 Глюкоза")],
            [KeyboardButton(text="😴 Сон"), KeyboardButton(text="😌 Самочувствие")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите показатель…",
    )

def remove_kb():
    return ReplyKeyboardRemove()

def history_filter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сегодня", callback_data="hist:filter:today"),
                InlineKeyboardButton(text="7 дней", callback_data="hist:filter:7d"),
                InlineKeyboardButton(text="Все", callback_data="hist:filter:all"),
            ],
            [InlineKeyboardButton(text="📅 Период…", callback_data="hist:filter:range")],
        ]
    )

def history_page_kb(page: int, total: int, page_size: int, flt: str, items=None) -> InlineKeyboardMarkup:
    max_page = (max(total - 1, 0) // page_size) if total > 0 else 0
    buttons = []

    # строки редактирования/удаления (по 10 записей максимум)
    if items:
        for idx, m in enumerate(items, start=1):
            buttons.append([
                InlineKeyboardButton(text=f"✏️ {idx}", callback_data=f"hist:edit:{m.id}:{page}:{flt}"),
                InlineKeyboardButton(text=f"🗑 {idx}", callback_data=f"hist:del:{m.id}:{page}:{flt}"),
            ])

    # пагинация
    prev_disabled = (page <= 0)
    next_disabled = (page >= max_page)

    buttons.append([
        InlineKeyboardButton(
            text="⬅️" if not prev_disabled else " ",
            callback_data=f"hist:page:{page-1}:{flt}" if not prev_disabled else "hist:noop"
        ),
        InlineKeyboardButton(text=f"{page+1}/{max_page+1}", callback_data="hist:noop"),
        InlineKeyboardButton(
            text="➡️" if not next_disabled else " ",
            callback_data=f"hist:page:{page+1}:{flt}" if not next_disabled else "hist:noop"
        )
    ])

    buttons.append([InlineKeyboardButton(text="🔎 Фильтр", callback_data="hist:open_filters")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def reminders_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить", callback_data="rem:add")],
            [InlineKeyboardButton(text="🔄 Обновить список", callback_data="rem:list")],
        ]
    )

def reminders_list_kb(items) -> InlineKeyboardMarkup:
    rows = []
    for r in items:
        status = "✅" if r.enabled else "⛔"
        rows.append([
            InlineKeyboardButton(text=f"{status} {r.time.strftime('%H:%M')}", callback_data=f"rem:toggle:{r.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"rem:del:{r.id}")
        ])
    rows.append([InlineKeyboardButton(text="➕ Добавить", callback_data="rem:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True,
        input_field_placeholder="Можно написать: отмена",
    )

def menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 Меню")]],
        resize_keyboard=True,
    )

def stats_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌡 Температура", callback_data="stats:metric:temperature")],
            [InlineKeyboardButton(text="❤️ Пульс", callback_data="stats:metric:pulse")],
            [InlineKeyboardButton(text="🩸 Давление", callback_data="stats:metric:pressure")],
            [InlineKeyboardButton(text="⚖️ Вес", callback_data="stats:metric:weight")],
            [InlineKeyboardButton(text="🫁 SpO₂", callback_data="stats:metric:spo2")],
            [InlineKeyboardButton(text="🍬 Глюкоза", callback_data="stats:metric:glucose")],
            [InlineKeyboardButton(text="😴 Сон", callback_data="stats:metric:sleep")],
            [InlineKeyboardButton(text="😌 Самочувствие", callback_data="stats:metric:wellbeing")],
        ]
    )

def stats_period_kb(metric: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="7 дней", callback_data=f"stats:period:{metric}:7d"),
                InlineKeyboardButton(text="30 дней", callback_data=f"stats:period:{metric}:30d"),
            ],
            [InlineKeyboardButton(text="📅 Период…", callback_data=f"stats:period:{metric}:range")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="stats:back")],
        ]
    )

def confirm_delete_kb(mid: int, page: int, flt: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"hist:del_yes:{mid}:{page}:{flt}"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"hist:del_no:{page}:{flt}"),
            ]
        ]
    )

def edit_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="hist:edit_cancel")]
        ]
    )