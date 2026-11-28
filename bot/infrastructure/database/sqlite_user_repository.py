from datetime import datetime, timezone
from typing import Optional

from bot.infrastructure.database.sqlite_connection import SQLiteConnectionManager


class SQLiteUserRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        self._connection_manager = connection_manager

    async def initialize(self) -> None:
        async with self._connection_manager.connect() as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    tg_user_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT,
                    email TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def upsert_user(
        self,
        tg_user_id: int,
        name: str,
        username: Optional[str] = None,
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_username = username.strip() if username else None
        async with self._connection_manager.connect() as db:
            cursor = await db.execute(
                "SELECT 1 FROM users WHERE tg_user_id = ?",
                (tg_user_id,),
            )
            exists = await cursor.fetchone() is not None

            if exists:
                await db.execute(
                    """
                    UPDATE users
                    SET name = ?,
                        username = COALESCE(?, username),
                        updated_at = ?
                    WHERE tg_user_id = ?
                    """,
                    (name, clean_username, now_iso, tg_user_id),
                )
            else:
                await db.execute(
                    """
                    INSERT INTO users (tg_user_id, name, username, email, created_at, updated_at)
                    VALUES (?, ?, ?, NULL, ?, ?)
                    """,
                    (tg_user_id, name, clean_username, now_iso, now_iso),
                )
            await db.commit()

    async def get_email(self, tg_user_id: int) -> Optional[str]:
        async with self._connection_manager.connect() as db:
            cursor = await db.execute(
                "SELECT email FROM users WHERE tg_user_id = ?",
                (tg_user_id,),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            (email,) = row
            return email

    async def save_email(
        self,
        tg_user_id: int,
        email: str,
        name: str = "",
        username: Optional[str] = None,
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_username = username.strip() if username else None
        async with self._connection_manager.connect() as db:
            cursor = await db.execute(
                "SELECT 1 FROM users WHERE tg_user_id = ?",
                (tg_user_id,),
            )
            exists = await cursor.fetchone() is not None

            if exists:
                await db.execute(
                    """
                    UPDATE users
                    SET email = ?,
                        name = COALESCE(NULLIF(?, ''), name),
                        username = COALESCE(?, username),
                        updated_at = ?
                    WHERE tg_user_id = ?
                    """,
                    (email, name, clean_username, now_iso, tg_user_id),
                )
            else:
                await db.execute(
                    """
                    INSERT INTO users (tg_user_id, name, username, email, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (tg_user_id, name, clean_username, email, now_iso, now_iso),
                )
            await db.commit()
