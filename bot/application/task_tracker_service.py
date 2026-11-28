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
from bot.localization.translator import Translator


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
        translator: Translator,
    ) -> None:
        self._task_repository = task_repository
        self._user_settings_repository = user_settings_repository
        self._lead_repository = lead_repository
        self._currency_provider = currency_provider
        self._weather_provider = weather_provider
        self._email_dispatcher = email_dispatcher
        self._lead_recipient_email = lead_recipient_email.strip()
        self._translator = translator

    async def record_task(
        self,
        user_id: int,
        title: str,
        hours: float,
        task_id: int | None = None,
    ) -> TaskEntry:
        now = datetime.now(timezone.utc)
        return await self._task_repository.add_task(
            user_id=user_id,
            title=title.strip(),
            hours=round(hours, 2),
            created_at=now,
            task_id=task_id,
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

    async def get_recent_today_tasks(
        self,
        user_id: int,
        limit: int = 7,
    ) -> list[TaskEntry]:
        today = datetime.now(timezone.utc).date()
        tasks = await self._task_repository.get_tasks_for_date(user_id, today)
        sorted_tasks = sorted(tasks, key=lambda t: t.updated_at, reverse=True)
        return sorted_tasks[:limit]

    async def build_market_weather_info(self) -> str:
        weather = await self._weather_provider.get_current_weather()
        currency_rate = await self._currency_provider.get_usd_rate()

        lines: list[str] = []

        if weather:
            lines.append(
                self._translator.get(
                    "reports.weather_info",
                    city=weather.city,
                    temperature=weather.temperature_c,
                    wind_speed=weather.wind_speed_kmh,
                )
            )
        else:
            lines.append(self._translator.get("reports.weather_unavailable"))

        if currency_rate:
            lines.append(
                self._translator.get(
                    "reports.currency_info",
                    code=currency_rate.code,
                    rate=currency_rate.rate_byn,
                )
            )
        else:
            lines.append(self._translator.get("reports.currency_unavailable"))

        lines.append(self._translator.get("reports.rest_api_showcase"))
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
        subject = self._translator.get(
            "emails.daily_report_subject",
            date=briefing.report_date.strftime("%d.%m.%Y"),
        )
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
            subject = self._translator.get(
                "emails.lead_subject",
                budget=lead.budget_usd,
            )
            body = self._translator.get(
                "emails.lead_body",
                created_at=lead.created_at.strftime("%d.%m.%Y %H:%M"),
                username=lead.username,
                user_id=lead.user_id,
                contact=lead.contact,
                budget=lead.budget_usd,
                description=lead.description,
            )
            await self._email_dispatcher.send_report(
                recipient_email=self._lead_recipient_email,
                subject=subject,
                body=body,
            )

        return lead

    def format_duration(self, hours: float) -> str:
        total_minutes = round(hours * 60)
        whole_hours, minutes = divmod(total_minutes, 60)
        if whole_hours > 0 and minutes > 0:
            return self._translator.get(
                "reports.duration_hours_minutes",
                hours=whole_hours,
                minutes=minutes,
            )
        if whole_hours > 0:
            return self._translator.get(
                "reports.duration_hours",
                hours=whole_hours,
            )
        return self._translator.get(
            "reports.duration_minutes",
            minutes=minutes,
        )

    def format_plain_report(self, briefing: DailyBriefing) -> str:
        lines = [
            self._translator.get(
                "reports.daily_header",
                date=briefing.report_date.strftime("%d.%m.%Y"),
            ),
            self._translator.get(
                "reports.daily_total_hours",
                total_duration=self.format_duration(briefing.total_hours),
            ),
            "",
            self._translator.get("reports.daily_tasks_title"),
        ]

        if not briefing.tasks:
            lines.append(self._translator.get("reports.daily_no_tasks"))
        else:
            for index, task in enumerate(briefing.tasks, start=1):
                lines.append(
                    self._translator.get(
                        "reports.daily_task_item",
                        index=index,
                        title=task.title,
                        duration=self.format_duration(task.hours),
                    )
                )

        return "\n".join(lines)
