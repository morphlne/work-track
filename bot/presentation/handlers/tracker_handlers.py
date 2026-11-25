import re

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.application.task_tracker_service import TaskTrackerService
from bot.presentation.keyboards.main_menu import (
    ADD_TASK_BUTTON,
    BUSINESS_PROJECT_BUTTON,
    CANCEL_BUTTON,
    CHANGE_EMAIL_BUTTON,
    SEND_EMAIL_BUTTON,
    TODAY_SUMMARY_BUTTON,
    WEATHER_CURRENCY_BUTTON,
    build_cancel_keyboard,
    build_main_menu_keyboard,
)
from bot.presentation.states.tracker_states import (
    EmailInputState,
    LeadRequestState,
    TaskInputState,
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def build_tracker_router(tracker_service: TaskTrackerService) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def handle_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            "Привет! Я помогу вести учёт задач и времени за день, "
            "отправлять сводку на почту, а также проверять погоду и курс валют.",
            reply_markup=build_main_menu_keyboard(),
        )

    @router.message(F.text == CANCEL_BUTTON)
    async def handle_cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            "Действие отменено.",
            reply_markup=build_main_menu_keyboard(),
        )

    @router.message(F.text == ADD_TASK_BUTTON)
    async def handle_add_task_start(message: Message, state: FSMContext) -> None:
        await state.set_state(TaskInputState.waiting_for_title)
        await message.answer(
            "Введите название задачи:",
            reply_markup=build_cancel_keyboard(),
        )

    @router.message(TaskInputState.waiting_for_title)
    async def handle_task_title(message: Message, state: FSMContext) -> None:
        title = (message.text or "").strip()
        if not title:
            await message.answer("Название не может быть пустым. Попробуйте ещё раз:")
            return

        await state.update_data(task_title=title)
        await state.set_state(TaskInputState.waiting_for_hours)
        await message.answer(
            "Сколько часов вы потратили на эту задачу? (например: 1.5 или 2)",
            reply_markup=build_cancel_keyboard(),
        )

    @router.message(TaskInputState.waiting_for_hours)
    async def handle_task_hours(message: Message, state: FSMContext) -> None:
        raw_value = (message.text or "").strip().replace(",", ".")
        try:
            hours = float(raw_value)
        except ValueError:
            await message.answer("Введите число, например 0.5 или 2:")
            return

        if hours <= 0 or hours > 24:
            await message.answer("Укажите корректное время от 0.1 до 24 часов:")
            return

        data = await state.get_data()
        task_title = data["task_title"]
        entry = await tracker_service.record_task(
            user_id=message.from_user.id,
            title=task_title,
            hours=hours,
        )

        await state.clear()
        await message.answer(
            f"✅ Сохранено: «{entry.title}» — {entry.hours:g} ч.",
            reply_markup=build_main_menu_keyboard(),
        )

    @router.message(F.text == TODAY_SUMMARY_BUTTON)
    async def handle_today_summary(message: Message, state: FSMContext) -> None:
        await state.clear()
        briefing = await tracker_service.build_daily_briefing(message.from_user.id)
        report_text = tracker_service.format_plain_report(briefing)
        await message.answer(
            report_text,
            reply_markup=build_main_menu_keyboard(),
        )

    @router.message(F.text == WEATHER_CURRENCY_BUTTON)
    async def handle_weather_and_currency(message: Message, state: FSMContext) -> None:
        await state.clear()
        info_text = await tracker_service.build_market_weather_info()
        await message.answer(
            info_text,
            reply_markup=build_main_menu_keyboard(),
        )

    @router.message(F.text == CHANGE_EMAIL_BUTTON)
    async def handle_change_email_start(message: Message, state: FSMContext) -> None:
        saved_email = await tracker_service.get_saved_email(message.from_user.id)
        await state.set_state(EmailInputState.waiting_for_email)
        await state.update_data(send_after_save=False)

        prompt = (
            f"Текущий адрес: {saved_email}\nВведите новый Email:"
            if saved_email
            else "Введите Email, который нужно сохранить для отчётов:"
        )
        await message.answer(prompt, reply_markup=build_cancel_keyboard())

    @router.message(F.text == SEND_EMAIL_BUTTON)
    async def handle_send_email_start(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        saved_email = await tracker_service.get_saved_email(user_id)

        if not saved_email:
            await state.set_state(EmailInputState.waiting_for_email)
            await state.update_data(send_after_save=True)
            await message.answer(
                "Email ещё не сохранён. Введите адрес, на который отправить отчёт:",
                reply_markup=build_cancel_keyboard(),
            )
            return

        await message.answer(f"Отправляю отчёт на {saved_email}...")
        try:
            await tracker_service.send_daily_report_to_email(
                user_id=user_id,
                recipient_email=saved_email,
            )
        except Exception:
            await message.answer(
                "Не удалось отправить письмо. Проверьте настройки SMTP в .env.",
                reply_markup=build_main_menu_keyboard(),
            )
            return

        await message.answer(
            f"📨 Итог за сегодня отправлен на {saved_email}.",
            reply_markup=build_main_menu_keyboard(),
        )

    @router.message(EmailInputState.waiting_for_email)
    async def handle_email_recipient(message: Message, state: FSMContext) -> None:
        recipient_email = (message.text or "").strip()
        if not EMAIL_PATTERN.match(recipient_email):
            await message.answer("Некорректный формат Email. Попробуйте ещё раз:")
            return

        user_id = message.from_user.id
        data = await state.get_data()
        send_after_save = data.get("send_after_save", True)

        await tracker_service.save_user_email(user_id, recipient_email)
        await state.clear()

        if not send_after_save:
            await message.answer(
                f"✅ Email {recipient_email} сохранён.",
                reply_markup=build_main_menu_keyboard(),
            )
            return

        await message.answer(f"Email сохранён. Отправляю отчёт на {recipient_email}...")
        try:
            await tracker_service.send_daily_report_to_email(
                user_id=user_id,
                recipient_email=recipient_email,
            )
        except Exception:
            await message.answer(
                "Email сохранён, но не удалось отправить письмо. Проверьте настройки SMTP в .env.",
                reply_markup=build_main_menu_keyboard(),
            )
            return

        await message.answer(
            f"📨 Итог за сегодня отправлен на {recipient_email}.",
            reply_markup=build_main_menu_keyboard(),
        )

    @router.message(F.text == BUSINESS_PROJECT_BUTTON)
    async def handle_business_project_start(message: Message, state: FSMContext) -> None:
        await state.set_state(LeadRequestState.waiting_for_description)
        await message.answer(
            "Опишите задачу для вашего бизнеса, вставьте текст вакансии или ссылку:",
            reply_markup=build_cancel_keyboard(),
        )

    @router.message(LeadRequestState.waiting_for_description)
    async def handle_lead_description(message: Message, state: FSMContext) -> None:
        description = (message.text or "").strip()
        if not description:
            await message.answer("Описание не может быть пустым. Попробуйте ещё раз:")
            return

        await state.update_data(lead_description=description)
        await state.set_state(LeadRequestState.waiting_for_budget)
        await message.answer(
            "Укажите планируемый бюджет или вилку оплаты в USD:",
            reply_markup=build_cancel_keyboard(),
        )

    @router.message(LeadRequestState.waiting_for_budget)
    async def handle_lead_budget(message: Message, state: FSMContext) -> None:
        budget_usd = (message.text or "").strip()
        if not budget_usd:
            await message.answer("Укажите бюджет или оплату в USD:")
            return

        normalized_budget = budget_usd.replace(",", ".").replace("$", "").strip()
        try:
            if float(normalized_budget) <= 0:
                await message.answer(
                    "Бюджет должен быть больше нуля. Укажите сумму в USD:"
                )
                return
        except ValueError:
            pass

        user = message.from_user
        tg_username = f"@{user.username}" if user and user.username else ""
        saved_email = await tracker_service.get_saved_email(user.id)

        contact_parts = [part for part in (tg_username, saved_email) if part]

        if contact_parts:
            data = await state.get_data()
            auto_contact = ", ".join(contact_parts)
            display_username = tg_username or (user.full_name if user else "Без username")

            try:
                await tracker_service.submit_lead_request(
                    user_id=user.id,
                    username=display_username,
                    description=data["lead_description"],
                    budget_usd=budget_usd,
                    contact=auto_contact,
                )
            except Exception:
                await state.clear()
                await message.answer(
                    "Заявка сохранена в базе, но не удалось отправить уведомление на почту.",
                    reply_markup=build_main_menu_keyboard(),
                )
                return

            await state.clear()
            await message.answer(
                f"✅ Спасибо! Заявка принята.\n"
                f"Бюджет: {budget_usd} USD\n"
                f"Контакт для связи: {auto_contact}",
                reply_markup=build_main_menu_keyboard(),
            )
            return

        await state.update_data(lead_budget=budget_usd)
        await state.set_state(LeadRequestState.waiting_for_contact)
        await message.answer(
            "У вас не задан @username в Telegram и не сохранён Email."
            "Укажите контакт для связи (Email или телефон):",
            reply_markup=build_cancel_keyboard(),
        )

    @router.message(LeadRequestState.waiting_for_contact)
    async def handle_lead_contact(message: Message, state: FSMContext) -> None:
        contact = (message.text or "").strip()
        if not contact:
            await message.answer("Контакт не может быть пустым. Введите Email или телефон:")
            return

        user = message.from_user
        data = await state.get_data()
        display_username = user.full_name if user else "Без username"

        try:
            await tracker_service.submit_lead_request(
                user_id=user.id,
                username=display_username,
                description=data["lead_description"],
                budget_usd=data["lead_budget"],
                contact=contact,
            )
        except Exception:
            await state.clear()
            await message.answer(
                "Заявка сохранена в базе, но не удалось отправить уведомление на почту.",
                reply_markup=build_main_menu_keyboard(),
            )
            return

        await state.clear()
        await message.answer(
            f"✅ Спасибо! Заявка принята."
            f"Бюджет: {data['lead_budget']} USD"
            f"Контакт для связи: {contact}",
            reply_markup=build_main_menu_keyboard(),
        )

    return router
