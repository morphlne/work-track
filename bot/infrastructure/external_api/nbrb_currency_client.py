import json
import logging
from typing import Optional

import aiohttp

from bot.domain.entities import CurrencyRate
from bot.domain.interfaces import CacheStorage

logger = logging.getLogger(__name__)


class NbrbCurrencyClient:
    API_URL = "https://api.nbrb.by/exrates/rates/USD?parammode=2"
    CACHE_KEY = "nbrb_usd_rate"

    def __init__(
        self,
        session: aiohttp.ClientSession,
        cache_storage: CacheStorage,
        cache_ttl_seconds: int,
    ) -> None:
        self._session = session
        self._cache_storage = cache_storage
        self._cache_ttl_seconds = cache_ttl_seconds

    async def get_usd_rate(self) -> Optional[CurrencyRate]:
        cached_raw = await self._cache_storage.get(self.CACHE_KEY)
        if cached_raw:
            return self._deserialize(cached_raw)

        try:
            async with self._session.get(
                self.API_URL,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except Exception as error:
            logger.warning("Failed to fetch NBRB currency rate: %s", error)
            return None

        rate = CurrencyRate(
            code=str(data.get("Cur_Abbreviation", "USD")),
            rate_byn=float(data["Cur_OfficialRate"]),
            scale=int(data.get("Cur_Scale", 1)),
        )
        await self._cache_storage.set(
            self.CACHE_KEY,
            self._serialize(rate),
            self._cache_ttl_seconds,
        )
        return rate

    @staticmethod
    def _serialize(rate: CurrencyRate) -> str:
        return json.dumps(
            {
                "code": rate.code,
                "rate_byn": rate.rate_byn,
                "scale": rate.scale,
            }
        )

    @staticmethod
    def _deserialize(raw: str) -> CurrencyRate:
        parsed = json.loads(raw)
        return CurrencyRate(
            code=parsed["code"],
            rate_byn=float(parsed["rate_byn"]),
            scale=int(parsed["scale"]),
        )
