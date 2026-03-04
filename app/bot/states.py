from aiogram.fsm.state import StatesGroup, State

class AddMeasurement(StatesGroup):
    choosing_type = State()
    entering_value = State()

class History(StatesGroup):
    entering_range = State()

class Reminders(StatesGroup):
    entering_time = State()

class Stats(StatesGroup):
    entering_range = State()