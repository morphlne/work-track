from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.localization.translator import Translator


def build_main_menu_keyboard(translator: Translator) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=translator.get("buttons.add_task"))],
            [
                KeyboardButton(text=translator.get("buttons.today_summary")),
                KeyboardButton(text=translator.get("buttons.weather_currency")),
            ],
            [
                KeyboardButton(text=translator.get("buttons.send_email")),
                KeyboardButton(text=translator.get("buttons.change_email")),
            ],
            [KeyboardButton(text=translator.get("buttons.business_project"))],
        ],
        resize_keyboard=True,
    )


def build_cancel_keyboard(translator: Translator) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=translator.get("buttons.cancel"))]],
        resize_keyboard=True,
    )
