from datetime import date, datetime

from bot.domain.entities import TaskEntry
from bot.infrastructure.database.sqlite_connection import SQLiteConnectionManager


class SQLiteTaskRepository:
    def __init__(self, connection_manager: SQLiteConnectionManager) -> None:
        self._connection_manager = connection_manager

    async def initialize(self) -> None:
        async with self._connection_manager.connect() as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    hours REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_user_date ON tasks (tg_user_id, created_at)"
            )
            await db.commit()

    async def add_task(
        self,
        tg_user_id: int,
        title: str,
        hours: float,
        created_at: datetime,
        task_id: int | None = None,
    ) -> TaskEntry:
        now_iso = created_at.isoformat()
        clean_title = title.strip()

        async with self._connection_manager.connect() as db:
            if task_id is not None:
                cursor = await db.execute(
                    "SELECT id, title, hours, created_at FROM tasks WHERE id = ? AND tg_user_id = ?",
                    (task_id, tg_user_id),
                )
                row = await cursor.fetchone()
                if row is not None:
                    updated_hours = round(float(row[2]) + hours, 2)
                    await db.execute(
                        "UPDATE tasks SET hours = ?, updated_at = ? WHERE id = ?",
                        (updated_hours, now_iso, task_id),
                    )
                    await db.commit()
                    return TaskEntry(
                        id=row[0],
                        tg_user_id=tg_user_id,
                        title=row[1],
                        hours=updated_hours,
                        created_at=datetime.fromisoformat(row[3]),
                        updated_at=created_at,
                    )

            cursor = await db.execute(
                """
                INSERT INTO tasks (tg_user_id, title, hours, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tg_user_id, clean_title, hours, now_iso, now_iso),
            )
            await db.commit()
            new_id = cursor.lastrowid or 0

        return TaskEntry(
            id=new_id,
            tg_user_id=tg_user_id,
            title=clean_title,
            hours=hours,
            created_at=created_at,
            updated_at=created_at,
        )

    async def get_tasks_for_date(
        self,
        tg_user_id: int,
        target_date: date,
    ) -> list[TaskEntry]:
        date_prefix = f"{target_date.isoformat()}%"
        async with self._connection_manager.connect() as db:
            cursor = await db.execute(
                """
                SELECT id, tg_user_id, title, hours, created_at, updated_at
                FROM tasks
                WHERE tg_user_id = ? AND created_at LIKE ?
                ORDER BY id ASC
                """,
                (tg_user_id, date_prefix),
            )
            rows = await cursor.fetchall()

        return [
            TaskEntry(
                id=row[0],
                tg_user_id=row[1],
                title=row[2],
                hours=row[3],
                created_at=datetime.fromisoformat(row[4]),
                updated_at=datetime.fromisoformat(row[5] or row[4]),
            )
            for row in rows
        ]
