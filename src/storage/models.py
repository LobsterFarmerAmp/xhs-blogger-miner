from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class Blogger:
    user_id: str
    nickname: str = ""
    avatar: str = ""
    description: str = ""
    gender: str = ""
    ip_location: str = ""
    followers_count: int = 0
    following_count: int = 0
    total_likes: int = 0
    homepage_url: str = ""
    crawled_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class Post:
    note_id: str
    blogger_user_id: str
    type: str = ""
    title: str = ""
    description: str = ""
    publish_time: int = 0
    last_update_time: int = 0
    note_url: str = ""
    liked_count_raw: str = ""
    liked_count_value: int = 0
    collected_count_raw: str = ""
    collected_count_value: int = 0
    comment_count_raw: str = ""
    comment_count_value: int = 0
    share_count_raw: str = ""
    share_count_value: int = 0
    image_urls: list[str] = field(default_factory=list)
    video_url: str = ""
    tag_list: list[str] = field(default_factory=list)
    ip_location: str = ""
    xsec_token: str = ""
    listing_data: str = ""
    crawled_at: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class CrawlLog:
    blogger_user_id: str
    started_at: str
    finished_at: str
    posts_found: int
    posts_new: int
    status: str
    error_message: str = ""
    id: int | None = None


CREATE_BLOGGERS_TABLE = """
CREATE TABLE IF NOT EXISTS bloggers (
    user_id TEXT PRIMARY KEY,
    nickname TEXT,
    avatar TEXT,
    description TEXT,
    gender TEXT,
    ip_location TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    total_likes INTEGER,
    homepage_url TEXT,
    crawled_at TEXT
);
"""

CREATE_POSTS_TABLE = """
CREATE TABLE IF NOT EXISTS posts (
    note_id TEXT PRIMARY KEY,
    blogger_user_id TEXT NOT NULL,
    type TEXT,
    title TEXT,
    description TEXT,
    publish_time INTEGER,
    last_update_time INTEGER,
    note_url TEXT,
    liked_count_raw TEXT,
    liked_count_value INTEGER,
    collected_count_raw TEXT,
    collected_count_value INTEGER,
    comment_count_raw TEXT,
    comment_count_value INTEGER,
    share_count_raw TEXT,
    share_count_value INTEGER,
    image_urls TEXT,
    video_url TEXT,
    tag_list TEXT,
    ip_location TEXT,
    xsec_token TEXT,
    listing_data TEXT,
    crawled_at TEXT,
    FOREIGN KEY (blogger_user_id) REFERENCES bloggers(user_id)
);
"""

CREATE_CRAWL_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS crawl_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blogger_user_id TEXT,
    started_at TEXT,
    finished_at TEXT,
    posts_found INTEGER,
    posts_new INTEGER,
    status TEXT,
    error_message TEXT
);
"""

CREATE_POSTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_posts_blogger_user_id
ON posts(blogger_user_id);
CREATE INDEX IF NOT EXISTS idx_posts_publish_time
ON posts(blogger_user_id, publish_time DESC);
"""

CREATE_CRAWL_LOGS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_crawl_logs_blogger_user_id
ON crawl_logs(blogger_user_id);
"""

TABLE_DDL = (
    CREATE_BLOGGERS_TABLE,
    CREATE_POSTS_TABLE,
    CREATE_CRAWL_LOGS_TABLE,
    CREATE_POSTS_INDEXES,
    CREATE_CRAWL_LOGS_INDEXES,
)
