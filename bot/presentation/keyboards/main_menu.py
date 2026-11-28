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


def build_task_duration_keyboard(translator: Translator) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=translator.get("buttons.time_15m")),
                KeyboardButton(text=translator.get("buttons.time_30m")),
                KeyboardButton(text=translator.get("buttons.time_45m")),
            ],
            [
                KeyboardButton(text=translator.get("buttons.time_1h")),
                KeyboardButton(text=translator.get("buttons.time_2h")),
                KeyboardButton(text=translator.get("buttons.time_3h")),
            ],
            [
                KeyboardButton(text=translator.get("buttons.time_4h")),
                KeyboardButton(text=translator.get("buttons.time_5h")),
                KeyboardButton(text=translator.get("buttons.time_6h")),
            ],
            [
                KeyboardButton(text=translator.get("buttons.time_7h")),
                KeyboardButton(text=translator.get("buttons.time_8h")),
                KeyboardButton(text=translator.get("buttons.cancel")),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=translator.get("messages.select_time_placeholder"),
    )


def build_task_title_keyboard(
    translator: Translator,
    recent_titles: list[str],
) -> ReplyKeyboardMarkup:
    buttons = [KeyboardButton(text=title) for title in recent_titles[:7]]
    buttons.append(KeyboardButton(text=translator.get("buttons.cancel")))

    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder=translator.get("messages.select_or_type_task_placeholder"),
    )
