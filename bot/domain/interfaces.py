from datetime import date, datetime
from typing import Optional, Protocol

from bot.domain.entities import CurrencyRate, LeadRequest, TaskEntry, WeatherSnapshot


class TaskRepository(Protocol):
    async def initialize(self) -> None: ...

    async def add_task(
        self,
        user_id: int,
        title: str,
        hours: float,
        created_at: datetime,
    ) -> TaskEntry: ...

    async def get_tasks_for_date(
        self,
        user_id: int,
        target_date: date,
    ) -> list[TaskEntry]: ...


class UserSettingsRepository(Protocol):
    async def initialize(self) -> None: ...

    async def get_email(self, user_id: int) -> Optional[str]: ...

    async def save_email(self, user_id: int, email: str) -> None: ...


class LeadRepository(Protocol):
    async def initialize(self) -> None: ...

    async def add_lead(
        self,
        user_id: int,
        username: str,
        description: str,
        budget_usd: str,
        contact: str,
        created_at: datetime,
    ) -> LeadRequest: ...


class CacheStorage(Protocol):
    async def initialize(self) -> None: ...

    async def get(self, key: str) -> Optional[str]: ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class CurrencyProvider(Protocol):
    async def get_usd_rate(self) -> Optional[CurrencyRate]: ...


class WeatherProvider(Protocol):
    async def get_current_weather(self) -> Optional[WeatherSnapshot]: ...


class EmailDispatcher(Protocol):
    async def send_report(
        self,
        recipient_email: str,
        subject: str,
        body: str,
    ) -> None: ...
