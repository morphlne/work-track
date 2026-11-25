from datetime import datetime, timezone
from typing import Optional

from bot.infrastructure.database.sqlite_connection import SQLiteConnectionManager


class SQLiteUserSettingsRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        self._connection_manager = connection_manager

    async def initialize(self) -> None:
        async with self._connection_manager.connect() as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def get_email(self, user_id: int) -> Optional[str]:
        async with self._connection_manager.connect() as db:
            cursor = await db.execute(
                "SELECT email FROM user_settings WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def save_email(self, user_id: int, email: str) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        async with self._connection_manager.connect() as db:
            await db.execute(
                """
                INSERT INTO user_settings (user_id, email, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    email = excluded.email,
                    updated_at = excluded.updated_at
                """,
                (user_id, email, updated_at),
            )
            await db.commit()
