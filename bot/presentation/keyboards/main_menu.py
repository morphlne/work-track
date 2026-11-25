from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

ADD_TASK_BUTTON = "➕ Добавить задачу"
TODAY_SUMMARY_BUTTON = "📊 Итог за сегодня"
SEND_EMAIL_BUTTON = "📧 Отправить итог на Email"
CHANGE_EMAIL_BUTTON = "✉️ Изменить Email"
CANCEL_BUTTON = "❌ Отмена"


def build_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADD_TASK_BUTTON)],
            [KeyboardButton(text=TODAY_SUMMARY_BUTTON)],
            [
                KeyboardButton(text=SEND_EMAIL_BUTTON),
                KeyboardButton(text=CHANGE_EMAIL_BUTTON),
            ],
        ],
        resize_keyboard=True,
    )


def build_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_BUTTON)]],
        resize_keyboard=True,
    )
