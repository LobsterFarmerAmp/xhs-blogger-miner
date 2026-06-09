#!/usr/bin/env python3
"""Backfill title and publish_time from listing_data JSON for existing posts.

Uses two zero-API-call data sources already in the DB:
- display_title: present in listing API response, previously not extracted
- note_id first 8 hex chars: Unix timestamp seconds, previously not decoded

Run:
    uv run python scripts/backfill_listing_metadata.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path


def decode_note_id_timestamp(note_id: str) -> int:
    if len(note_id) >= 8:
        try:
            return int(note_id[:8], 16)
        except (ValueError, TypeError):
            pass
    return 0


def backfill(db_path: str, blogger_user_id: str | None = None) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    where = "WHERE blogger_user_id = ?" if blogger_user_id else ""
    params = (blogger_user_id,) if blogger_user_id else ()

    # Get all posts with listing_data
    rows = conn.execute(
        f"SELECT note_id, title, publish_time, listing_data FROM posts {where}",
        params,
    ).fetchall()

    total = len(rows)
    title_filled = 0
    time_filled = 0
    no_listing_data = 0
    parse_errors = 0

    for row in rows:
        note_id = row["note_id"]
        old_title = row["title"]
        old_time = row["publish_time"]
        listing_data = row["listing_data"]

        if not listing_data:
            no_listing_data += 1
            continue

        try:
            data = json.loads(listing_data)
        except (json.JSONDecodeError, TypeError):
            parse_errors += 1
            continue

        new_title = str(data.get("display_title") or data.get("title") or "")
        new_time = decode_note_id_timestamp(note_id)

        updates = []
        update_params = []

        if new_title and (not old_title or old_title != new_title):
            updates.append("title = ?")
            update_params.append(new_title)
            title_filled += 1

        if new_time > 0 and (not old_time or old_time == 0):
            updates.append("publish_time = ?")
            update_params.append(new_time)
            time_filled += 1

        if updates:
            update_params.append(note_id)
            sql = f"UPDATE posts SET {', '.join(updates)} WHERE note_id = ?"
            conn.execute(sql, update_params)

    conn.commit()
    conn.close()

    return {
        "total": total,
        "title_filled": title_filled,
        "time_filled": time_filled,
        "no_listing_data": no_listing_data,
        "parse_errors": parse_errors,
    }


def verify(db_path: str, blogger_user_id: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total = conn.execute(
        "SELECT COUNT(*) as c FROM posts WHERE blogger_user_id = ?",
        (blogger_user_id,),
    ).fetchone()["c"]

    with_title = conn.execute(
        "SELECT COUNT(*) as c FROM posts WHERE blogger_user_id = ? AND title IS NOT NULL AND title != ''",
        (blogger_user_id,),
    ).fetchone()["c"]

    with_time = conn.execute(
        "SELECT COUNT(*) as c FROM posts WHERE blogger_user_id = ? AND publish_time > 0",
        (blogger_user_id,),
    ).fetchone()["c"]

    conn.close()
    return {
        "total": total,
        "with_title": with_title,
        "with_publish_time": with_time,
        "missing_title": total - with_title,
        "missing_time": total - with_time,
    }


def main():
    db_path = os.environ.get(
        "XHS_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "xhs_bloggers.db"),
    )
    blogger_user_id = os.environ.get(
        "XHS_BLOGGER_ID",
        "5bc56aaac0f39e0001627d17",
    )

    print(f"DB: {db_path}")
    print(f"Blogger: {blogger_user_id}")

    # Before
    before = verify(db_path, blogger_user_id)
    print(f"\nBefore: {before['total']} posts, "
          f"{before['with_title']} with title, "
          f"{before['with_publish_time']} with publish_time")

    # Backfill
    result = backfill(db_path, blogger_user_id)
    print(f"\nBackfill:")
    print(f"  title filled: {result['title_filled']}")
    print(f"  publish_time filled: {result['time_filled']}")
    print(f"  no listing_data: {result['no_listing_data']}")
    print(f"  parse errors: {result['parse_errors']}")

    # After
    after = verify(db_path, blogger_user_id)
    print(f"\nAfter: {after['total']} posts, "
          f"{after['with_title']} with title, "
          f"{after['with_publish_time']} with publish_time")
    print(f"  missing title: {after['missing_title']}")
    print(f"  missing publish_time: {after['missing_time']}")

    if after["missing_title"] == 0 and after["missing_time"] == 0:
        print("\n✅ All posts now have title and publish_time!")
    else:
        print(f"\n⚠️  {after['missing_title']} still missing title, "
              f"{after['missing_time']} still missing publish_time")


if __name__ == "__main__":
    main()
