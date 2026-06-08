from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    CRAWLER_MAX_POSTS_PER_BLOGGER: int = 50
    CRAWLER_MAX_SLEEP_SEC: int = 10
    CRAWLER_MIN_SLEEP_SEC: int = 3
    SAVE_DATA_PATH: str = "data"
    LOG_LEVEL: str = "INFO"
    HEADLESS: bool = True
    COOKIES: str = ""
    XHS_CRAWLER_TYPE: str = "creator"
    DATABASE_PATH: str = "data/xhs_bloggers.db"
    CDP_DEBUG_PORT: int = 9222
    CDP_CONNECT_EXISTING: bool = False

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Settings":
        load_dotenv(dotenv_path=env_file)
        return cls(
            CRAWLER_MAX_POSTS_PER_BLOGGER=_get_int("CRAWLER_MAX_POSTS_PER_BLOGGER", 50),
            CRAWLER_MAX_SLEEP_SEC=_get_int("CRAWLER_MAX_SLEEP_SEC", 10),
            CRAWLER_MIN_SLEEP_SEC=_get_int("CRAWLER_MIN_SLEEP_SEC", 3),
            SAVE_DATA_PATH=os.getenv("SAVE_DATA_PATH", "data"),
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
            HEADLESS=_get_bool("HEADLESS", True),
            COOKIES=os.getenv("COOKIES", ""),
            XHS_CRAWLER_TYPE=os.getenv("XHS_CRAWLER_TYPE", "creator"),
            DATABASE_PATH=os.getenv("DATABASE_PATH", "data/xhs_bloggers.db"),
            CDP_DEBUG_PORT=_get_int("CDP_DEBUG_PORT", 9222),
            CDP_CONNECT_EXISTING=_get_bool("CDP_CONNECT_EXISTING", False),
        )


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(
            f"Environment variable {name} must be an integer, got: {raw!r}"
        ) from None


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    value = raw.strip().lower()
    if value not in {"1", "true", "yes", "y", "on", "0", "false", "no", "n", "off"}:
        raise ValueError(
            f"Environment variable {name} must be a boolean, got: {raw!r}"
        ) from None
    return value in {"1", "true", "yes", "y", "on"}
