from datetime import datetime

from bot.domain.entities import LeadRequest
from bot.infrastructure.database.sqlite_connection import SQLiteConnectionManager


class SQLiteLeadRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        self._connection_manager = connection_manager

    async def initialize(self) -> None:
        async with self._connection_manager.connect() as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_user_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    budget_usd TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def add_lead(
        self,
        tg_user_id: int,
        description: str,
        budget_usd: str,
        contact: str,
        created_at: datetime,
    ) -> LeadRequest:
        created_at_iso = created_at.isoformat()
        async with self._connection_manager.connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO leads (
                    tg_user_id,
                    description,
                    budget_usd,
                    contact,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (tg_user_id, description, budget_usd, contact, created_at_iso),
            )
            await db.commit()
            lead_id = cursor.lastrowid

        return LeadRequest(
            id=lead_id or 0,
            tg_user_id=tg_user_id,
            description=description,
            budget_usd=budget_usd,
            contact=contact,
            created_at=created_at,
        )
