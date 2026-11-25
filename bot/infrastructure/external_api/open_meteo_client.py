import json
import logging
from typing import Optional

import aiohttp

from bot.domain.entities import WeatherSnapshot
from bot.domain.interfaces import CacheStorage

logger = logging.getLogger(__name__)


class OpenMeteoClient:
    API_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        cache_storage: CacheStorage,
        latitude: float,
        longitude: float,
        city_name: str,
        cache_ttl_seconds: int,
    ) -> None:
        self._session = session
        self._cache_storage = cache_storage
        self._latitude = latitude
        self._longitude = longitude
        self._city_name = city_name
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_key = f"open_meteo:{latitude}:{longitude}"

    async def get_current_weather(self) -> Optional[WeatherSnapshot]:
        cached_raw = await self._cache_storage.get(self._cache_key)
        if cached_raw:
            return self._deserialize(cached_raw)

        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "current": "temperature_2m,wind_speed_10m",
        }

        try:
            async with self._session.get(
                self.API_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except Exception as error:
            logger.warning("Failed to fetch Open-Meteo weather: %s", error)
            return None

        current = data.get("current", {})
        snapshot = WeatherSnapshot(
            city=self._city_name,
            temperature_c=float(current["temperature_2m"]),
            wind_speed_kmh=float(current["wind_speed_10m"]),
        )
        await self._cache_storage.set(
            self._cache_key,
            self._serialize(snapshot),
            self._cache_ttl_seconds,
        )
        return snapshot

    @staticmethod
    def _serialize(snapshot: WeatherSnapshot) -> str:
        return json.dumps(
            {
                "city": snapshot.city,
                "temperature_c": snapshot.temperature_c,
                "wind_speed_kmh": snapshot.wind_speed_kmh,
            }
        )

    @staticmethod
    def _deserialize(raw: str) -> WeatherSnapshot:
        parsed = json.loads(raw)
        return WeatherSnapshot(
            city=parsed["city"],
            temperature_c=float(parsed["temperature_c"]),
            wind_speed_kmh=float(parsed["wind_speed_kmh"]),
        )
