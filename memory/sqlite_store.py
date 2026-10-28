import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from memory.item import MemoryItem


class SQLiteMemoryStore:
    """保存和读取本地单用户记忆。"""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def add(self, content: str) -> MemoryItem:
        """保存一条非空记忆，并返回记忆项。"""
        content = content.strip()
        if not content:
            raise ValueError("记忆内容不能为空")

        item = MemoryItem(
            id=str(uuid4()),
            content=content,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT INTO memories (id, content, created_at)
                VALUES (?, ?, ?)
                """,
                (item.id, item.content, item.created_at),
            )
            connection.commit()

        return item

    def get(self, memory_id: str) -> MemoryItem | None:
        """按标识读取记忆，不存在时返回 None。"""
        with closing(sqlite3.connect(self.db_path)) as connection:
            row = connection.execute(
                """
                SELECT id, content, created_at
                FROM memories
                WHERE id = ?
                """,
                (memory_id,),
            ).fetchone()

        if row is None:
            return None

        return MemoryItem(
            id=row[0],
            content=row[1],
            created_at=row[2],
        )