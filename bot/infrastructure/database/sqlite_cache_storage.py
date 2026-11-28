import time
from typing import Optional

from bot.infrastructure.database.sqlite_connection import SQLiteConnectionManager


class SQLiteCacheStorage:
    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        self._connection_manager = connection_manager

    async def initialize(self) -> None:
        async with self._connection_manager.connect() as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            await db.commit()

    async def get(self, key: str) -> Optional[str]:
        now_ts = int(time.time())
        async with self._connection_manager.connect() as db:
            cursor = await db.execute(
                "SELECT payload, expires_at FROM cache WHERE cache_key = ?",
                (key,),
            )
            row = await cursor.fetchone()
            if not row:
                return None

            payload, expires_at = row
            if expires_at <= now_ts:
                await db.execute("DELETE FROM cache WHERE cache_key = ?", (key,))
                await db.commit()
                return None

            return payload

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        expires_at = int(time.time()) + ttl_seconds
        async with self._connection_manager.connect() as db:
            await db.execute(
                """
                INSERT INTO cache (cache_key, payload, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    expires_at = excluded.expires_at
                """,
                (key, value, expires_at),
            )
            await db.commit()
