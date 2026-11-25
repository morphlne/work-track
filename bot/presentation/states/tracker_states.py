from aiogram.fsm.state import State, StatesGroup


class TaskInputState(StatesGroup):
    waiting_for_title = State()
    waiting_for_hours = State()


class EmailInputState(StatesGroup):
    waiting_for_email = State()


class LeadRequestState(StatesGroup):
    waiting_for_description = State()
    waiting_for_budget = State()
    waiting_for_contact = State()
