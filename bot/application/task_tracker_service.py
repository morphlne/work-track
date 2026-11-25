from datetime import datetime, timezone
from typing import Optional

from bot.domain.entities import DailyBriefing, LeadRequest, TaskEntry
from bot.domain.interfaces import (
    CurrencyProvider,
    EmailDispatcher,
    LeadRepository,
    TaskRepository,
    UserSettingsRepository,
    WeatherProvider,
)


class TaskTrackerService:
    def __init__(
        self,
        task_repository: TaskRepository,
        user_settings_repository: UserSettingsRepository,
        lead_repository: LeadRepository,
        currency_provider: CurrencyProvider,
        weather_provider: WeatherProvider,
        email_dispatcher: EmailDispatcher,
        lead_recipient_email: str,
    ) -> None:
        self._task_repository = task_repository
        self._user_settings_repository = user_settings_repository
        self._lead_repository = lead_repository
        self._currency_provider = currency_provider
        self._weather_provider = weather_provider
        self._email_dispatcher = email_dispatcher
        self._lead_recipient_email = lead_recipient_email.strip()

    async def record_task(
        self,
        user_id: int,
        title: str,
        hours: float,
    ) -> TaskEntry:
        now = datetime.now(timezone.utc)
        return await self._task_repository.add_task(
            user_id=user_id,
            title=title.strip(),
            hours=round(hours, 2),
            created_at=now,
        )

    async def build_daily_briefing(self, user_id: int) -> DailyBriefing:
        today = datetime.now(timezone.utc).date()
        tasks = await self._task_repository.get_tasks_for_date(user_id, today)
        total_hours = round(sum(task.hours for task in tasks), 2)

        return DailyBriefing(
            report_date=today,
            tasks=tasks,
            total_hours=total_hours,
        )

    async def build_market_weather_info(self) -> str:
        weather = await self._weather_provider.get_current_weather()
        currency_rate = await self._currency_provider.get_usd_rate()

        lines: list[str] = []

        if weather:
            lines.append(
                f"🌤 Погода ({weather.city}): "
                f"{weather.temperature_c:+.1f}°C, "
                f"ветер {weather.wind_speed_kmh:.1f} км/ч"
            )
        else:
            lines.append("🌤 Погода: данные временно недоступны")

        if currency_rate:
            lines.append(
                f"💵 Курс {currency_rate.code} (НБРБ): "
                f"{currency_rate.rate_byn:.4f} BYN"
            )
        else:
            lines.append("💵 Курс USD (НБРБ): данные временно недоступны")

        return "\n".join(lines)

    async def get_saved_email(self, user_id: int) -> Optional[str]:
        return await self._user_settings_repository.get_email(user_id)

    async def save_user_email(self, user_id: int, email: str) -> None:
        await self._user_settings_repository.save_email(user_id, email.strip())

    async def send_daily_report_to_email(
        self,
        user_id: int,
        recipient_email: str,
    ) -> DailyBriefing:
        briefing = await self.build_daily_briefing(user_id)
        subject = f"Отчёт по задачам за {briefing.report_date.strftime('%d.%m.%Y')}"
        body = self.format_plain_report(briefing)

        await self._email_dispatcher.send_report(
            recipient_email=recipient_email,
            subject=subject,
            body=body,
        )
        return briefing

    async def submit_lead_request(
        self,
        user_id: int,
        username: str,
        description: str,
        budget_usd: str,
        contact: str,
    ) -> LeadRequest:
        now = datetime.now(timezone.utc)
        lead = await self._lead_repository.add_lead(
            user_id=user_id,
            username=username,
            description=description.strip(),
            budget_usd=budget_usd.strip(),
            contact=contact.strip(),
            created_at=now,
        )

        if self._lead_recipient_email:
            subject = f"Новая заявка: проект под бизнес (${lead.budget_usd})"
            body = (
                f"Новая заявка из Telegram-бота WorkTrack\n"
                f"Дата (UTC): {lead.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"Telegram: {lead.username} (ID: {lead.user_id})\n"
                f"Контакт для связи: {lead.contact}\n"
                f"Оплата / бюджет (USD): {lead.budget_usd}\n\n"
                f"Описание / вакансия / ссылка:\n{lead.description}"
            )
            await self._email_dispatcher.send_report(
                recipient_email=self._lead_recipient_email,
                subject=subject,
                body=body,
            )

        return lead

    @staticmethod
    def format_plain_report(briefing: DailyBriefing) -> str:
        lines = [
            f"Итог за {briefing.report_date.strftime('%d.%m.%Y')}",
            f"Всего потрачено: {briefing.total_hours:g} ч.",
            "",
            "Выполненные задачи:",
        ]

        if not briefing.tasks:
            lines.append("— Задач за сегодня пока нет.")
        else:
            for index, task in enumerate(briefing.tasks, start=1):
                lines.append(f"{index}. {task.title} — {task.hours:g} ч.")

        return "\n".join(lines)
