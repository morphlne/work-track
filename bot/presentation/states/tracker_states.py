from aiogram.fsm.state import State, StatesGroup


class TaskInputState(StatesGroup):
    waiting_for_title = State()
    waiting_for_hours = State()


class EmailInputState(StatesGroup):
    waiting_for_email = State()
