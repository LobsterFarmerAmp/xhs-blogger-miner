from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterator

from src.storage.models import Blogger, CrawlLog, Post, TABLE_DDL


class Database:
    # Concurrency note: This implementation uses per-operation SQLite connections,
    # which is safe for the current single-blogger serial crawl model. If the
    # project adopts concurrent blogger collection (asyncio + multiple coroutines),
    # switch to aiosqlite or a connection-pooled approach to avoid contention.
    def __init__(self, database_path: str | Path = "data/xhs_bloggers.db") -> None:
        self.database_path = str(database_path)
        self._memory_connection: sqlite3.Connection | None = None
        if self.database_path == ":memory:":
            self._memory_connection = sqlite3.connect(":memory:")
            self._memory_connection.row_factory = sqlite3.Row

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        if self._memory_connection is not None:
            yield self._memory_connection
            self._memory_connection.commit()
            return

        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            for ddl in TABLE_DDL:
                conn.executescript(ddl)

    def upsert_blogger(self, blogger: Blogger | dict[str, Any]) -> None:
        data = _to_record(blogger)
        columns = list(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        assignments = ", ".join(
            f"{column} = excluded.{column}" for column in columns if column != "user_id"
        )
        sql = (
            f"INSERT INTO bloggers ({', '.join(columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT(user_id) DO UPDATE SET {assignments}"
        )
        with self.connection() as conn:
            conn.execute(sql, [data[column] for column in columns])

    def upsert_post(self, post: Post | dict[str, Any]) -> bool:
        data = _to_record(post)
        data["image_urls"] = _json_or_text(data.get("image_urls", []))
        data["tag_list"] = _json_or_text(data.get("tag_list", []))

        with self.connection() as conn:
            exists = conn.execute(
                "SELECT 1 FROM posts WHERE note_id = ?",
                (data["note_id"],),
            ).fetchone()
            columns = list(data.keys())
            placeholders = ", ".join("?" for _ in columns)
            assignments = ", ".join(
                f"{column} = excluded.{column}"
                for column in columns
                if column != "note_id"
            )
            sql = (
                f"INSERT INTO posts ({', '.join(columns)}) VALUES ({placeholders}) "
                f"ON CONFLICT(note_id) DO UPDATE SET {assignments}"
            )
            conn.execute(sql, [data[column] for column in columns])
            return exists is None

    def insert_crawl_log(self, crawl_log: CrawlLog | dict[str, Any]) -> int:
        data = _to_record(crawl_log)
        data.pop("id", None)
        columns = list(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        with self.connection() as conn:
            cursor = conn.execute(
                f"INSERT INTO crawl_logs ({', '.join(columns)}) VALUES ({placeholders})",
                [data[column] for column in columns],
            )
            return int(cursor.lastrowid)

    def get_bloggers(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM bloggers ORDER BY user_id").fetchall()
            return [dict(row) for row in rows]

    def get_posts_for_blogger(self, blogger_user_id: str) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM posts WHERE blogger_user_id = ? ORDER BY publish_time DESC",
                (blogger_user_id,),
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                for field in ("image_urls", "tag_list"):
                    raw = d.get(field)
                    if isinstance(raw, str):
                        try:
                            d[field] = json.loads(raw)
                        except json.JSONDecodeError:
                            d[field] = []
                result.append(d)
            return result

    def close(self) -> None:
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None


def _to_record(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    return dict(value)


def _json_or_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value or [], ensure_ascii=False)
