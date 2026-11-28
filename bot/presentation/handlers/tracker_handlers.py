import logging
import re

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.application.task_tracker_service import TaskTrackerService
from bot.localization.translator import Translator
from bot.presentation.keyboards.main_menu import (
    build_cancel_keyboard,
    build_main_menu_keyboard,
    build_task_duration_keyboard,
)
from bot.presentation.states.tracker_states import (
    EmailInputState,
    LeadRequestState,
    TaskInputState,
)

logger = logging.getLogger(__name__)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def build_tracker_router(
    tracker_service: TaskTrackerService,
    translator: Translator,
) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def handle_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            translator.get("messages.start"),
            reply_markup=build_main_menu_keyboard(translator),
        )

    @router.message(F.text == translator.get("buttons.cancel"))
    async def handle_cancel(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            translator.get("messages.cancelled"),
            reply_markup=build_main_menu_keyboard(translator),
        )

    @router.message(F.text == translator.get("buttons.add_task"))
    async def handle_add_task_start(message: Message, state: FSMContext) -> None:
        await state.set_state(TaskInputState.waiting_for_title)
        await message.answer(
            translator.get("messages.ask_task_title"),
            reply_markup=build_cancel_keyboard(translator),
        )

    @router.message(TaskInputState.waiting_for_title)
    async def handle_task_title(message: Message, state: FSMContext) -> None:
        title = (message.text or "").strip()
        if not title:
            await message.answer(translator.get("messages.empty_task_title"))
            return

        await state.update_data(task_title=title)
        await state.set_state(TaskInputState.waiting_for_hours)
        await message.answer(
            translator.get("messages.ask_task_hours"),
            reply_markup=build_task_duration_keyboard(translator),
        )

    @router.message(TaskInputState.waiting_for_hours)
    async def handle_task_hours(message: Message, state: FSMContext) -> None:
        duration_map = {
            translator.get("buttons.time_15m"): 0.25,
            translator.get("buttons.time_30m"): 0.5,
            translator.get("buttons.time_45m"): 0.75,
            translator.get("buttons.time_1h"): 1.0,
            translator.get("buttons.time_2h"): 2.0,
            translator.get("buttons.time_3h"): 3.0,
            translator.get("buttons.time_4h"): 4.0,
            translator.get("buttons.time_5h"): 5.0,
            translator.get("buttons.time_6h"): 6.0,
            translator.get("buttons.time_7h"): 7.0,
            translator.get("buttons.time_8h"): 8.0,
        }
        selected_text = (message.text or "").strip()
        hours = duration_map.get(selected_text)

        if hours is None and selected_text.isdigit():
            parsed_hours = int(selected_text)
            if 1 <= parsed_hours <= 8:
                hours = float(parsed_hours)

        if hours is None:
            await message.answer(
                translator.get("messages.invalid_hours_choice"),
                reply_markup=build_task_duration_keyboard(translator),
            )
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
            translator.get(
                "messages.task_saved",
                title=entry.title,
                hours=entry.hours,
            ),
            reply_markup=build_main_menu_keyboard(translator),
        )

    @router.message(F.text == translator.get("buttons.today_summary"))
    async def handle_today_summary(message: Message, state: FSMContext) -> None:
        await state.clear()
        briefing = await tracker_service.build_daily_briefing(message.from_user.id)
        report_text = tracker_service.format_plain_report(briefing)
        await message.answer(
            report_text,
            reply_markup=build_main_menu_keyboard(translator),
        )

    @router.message(F.text == translator.get("buttons.weather_currency"))
    async def handle_weather_and_currency(message: Message, state: FSMContext) -> None:
        await state.clear()
        info_text = await tracker_service.build_market_weather_info()
        await message.answer(
            info_text,
            reply_markup=build_main_menu_keyboard(translator),
        )

    @router.message(F.text == translator.get("buttons.change_email"))
    async def handle_change_email_start(message: Message, state: FSMContext) -> None:
        saved_email = await tracker_service.get_saved_email(message.from_user.id)
        await state.set_state(EmailInputState.waiting_for_email)
        await state.update_data(send_after_save=False)

        prompt = (
            translator.get("messages.change_email_current", email=saved_email)
            if saved_email
            else translator.get("messages.change_email_new")
        )
        await message.answer(prompt, reply_markup=build_cancel_keyboard(translator))

    @router.message(F.text == translator.get("buttons.send_email"))
    async def handle_send_email_start(message: Message, state: FSMContext) -> None:
        user_id = message.from_user.id
        saved_email = await tracker_service.get_saved_email(user_id)

        if not saved_email:
            await state.set_state(EmailInputState.waiting_for_email)
            await state.update_data(send_after_save=True)
            await message.answer(
                translator.get("messages.send_email_not_saved"),
                reply_markup=build_cancel_keyboard(translator),
            )
            return

        await message.answer(
            translator.get("messages.sending_report", email=saved_email)
        )
        try:
            await tracker_service.send_daily_report_to_email(
                user_id=user_id,
                recipient_email=saved_email,
            )
        except Exception:
            logger.exception("Email delivery failed")
            await message.answer(
                translator.get("messages.send_email_failed"),
                reply_markup=build_main_menu_keyboard(translator),
            )
            return

        await message.answer(
            translator.get("messages.send_email_success", email=saved_email),
            reply_markup=build_main_menu_keyboard(translator),
        )

    @router.message(EmailInputState.waiting_for_email)
    async def handle_email_recipient(message: Message, state: FSMContext) -> None:
        recipient_email = (message.text or "").strip()
        if not EMAIL_PATTERN.match(recipient_email):
            await message.answer(translator.get("messages.invalid_email_format"))
            return

        user_id = message.from_user.id
        data = await state.get_data()
        send_after_save = data.get("send_after_save", True)

        await tracker_service.save_user_email(user_id, recipient_email)
        await state.clear()

        if not send_after_save:
            await message.answer(
                translator.get("messages.email_saved", email=recipient_email),
                reply_markup=build_main_menu_keyboard(translator),
            )
            return

        await message.answer(
            translator.get("messages.email_saved_and_sending", email=recipient_email)
        )
        try:
            await tracker_service.send_daily_report_to_email(
                user_id=user_id,
                recipient_email=recipient_email,
            )
        except Exception:
            logger.exception("Email delivery failed")
            await message.answer(
                translator.get("messages.email_saved_but_send_failed"),
                reply_markup=build_main_menu_keyboard(translator),
            )
            return

        await message.answer(
            translator.get("messages.send_email_success", email=recipient_email),
            reply_markup=build_main_menu_keyboard(translator),
        )

    @router.message(F.text == translator.get("buttons.business_project"))
    async def handle_business_project_start(message: Message, state: FSMContext) -> None:
        await state.set_state(LeadRequestState.waiting_for_description)
        await message.answer(
            translator.get("messages.ask_lead_description"),
            reply_markup=build_cancel_keyboard(translator),
        )

    @router.message(LeadRequestState.waiting_for_description)
    async def handle_lead_description(message: Message, state: FSMContext) -> None:
        description = (message.text or "").strip()
        if not description:
            await message.answer(translator.get("messages.empty_lead_description"))
            return

        await state.update_data(lead_description=description)
        await state.set_state(LeadRequestState.waiting_for_budget)
        await message.answer(
            translator.get("messages.ask_lead_budget"),
            reply_markup=build_cancel_keyboard(translator),
        )

    @router.message(LeadRequestState.waiting_for_budget)
    async def handle_lead_budget(message: Message, state: FSMContext) -> None:
        budget_usd = (message.text or "").strip()
        if not budget_usd:
            await message.answer(translator.get("messages.empty_lead_budget"))
            return

        normalized_budget = budget_usd.replace(",", ".").replace("$", "").strip()
        try:
            if float(normalized_budget) <= 0:
                await message.answer(translator.get("messages.zero_lead_budget"))
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
                logger.exception("Email delivery failed")
                await state.clear()
                await message.answer(
                    translator.get("messages.lead_saved_email_failed"),
                    reply_markup=build_main_menu_keyboard(translator),
                )
                return

            await state.clear()
            await message.answer(
                translator.get(
                    "messages.lead_accepted",
                    budget=budget_usd,
                    contact=auto_contact,
                ),
                reply_markup=build_main_menu_keyboard(translator),
            )
            return

        await state.update_data(lead_budget=budget_usd)
        await state.set_state(LeadRequestState.waiting_for_contact)
        await message.answer(
            translator.get("messages.ask_lead_contact"),
            reply_markup=build_cancel_keyboard(translator),
        )

    @router.message(LeadRequestState.waiting_for_contact)
    async def handle_lead_contact(message: Message, state: FSMContext) -> None:
        contact = (message.text or "").strip()
        if not contact:
            await message.answer(translator.get("messages.empty_lead_contact"))
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
            logger.exception("Email delivery failed")
            await state.clear()
            await message.answer(
                translator.get("messages.lead_saved_email_failed"),
                reply_markup=build_main_menu_keyboard(translator),
            )
            return

        await state.clear()
        await message.answer(
            translator.get(
                "messages.lead_accepted",
                budget=data["lead_budget"],
                contact=contact,
            ),
            reply_markup=build_main_menu_keyboard(translator),
        )

    return router
