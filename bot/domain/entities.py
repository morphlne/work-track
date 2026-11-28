from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class TaskEntry:
    id: int
    user_id: int
    title: str
    hours: float
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CurrencyRate:
    code: str
    rate_byn: float
    scale: int


@dataclass(frozen=True)
class WeatherSnapshot:
    city: str
    temperature_c: float
    wind_speed_kmh: float


@dataclass(frozen=True)
class DailyBriefing:
    report_date: date
    tasks: list[TaskEntry]
    total_hours: float


@dataclass(frozen=True)
class LeadRequest:
    id: int
    user_id: int
    username: str
    description: str
    budget_usd: str
    contact: str
    created_at: datetime
