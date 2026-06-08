from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from src.config_loader import load_bloggers_config
from src.miner.crawler import BloggerCrawler, CrawlResult
from src.miner.human_sim import HumanSimulator
from src.storage.database import Database
from src.utils.crawler_helpers import extract_user_id
from src.utils.logger import setup_logger
from src.utils.reporter import Reporter, ReportSummary


class Pipeline:
    def __init__(self, config: Any, bloggers_config_path: str | Path | None = None) -> None:
        self.config = config
        self.bloggers_config = load_bloggers_config(bloggers_config_path)
        self.logger = setup_logger(level=config.LOG_LEVEL, data_path=config.SAVE_DATA_PATH)
        self._blogger_index: dict[str, dict[str, Any]] = {}
        for item in self.bloggers_config["bloggers"]:
            uid = extract_user_id(item)
            if uid:
                if uid in self._blogger_index:
                    self.logger.warning(
                        "Duplicate blogger user_id '%s' in config, "
                        "overriding previous entry", uid
                    )
                self._blogger_index[uid] = item
        self.db = Database(config.DATABASE_PATH)
        self.human_sim = HumanSimulator(
            min_delay_sec=config.CRAWLER_MIN_SLEEP_SEC,
            max_delay_sec=config.CRAWLER_MAX_SLEEP_SEC,
        )
        self.crawler = BloggerCrawler(config, self.db, self.human_sim)
        self.reporter = Reporter(config.SAVE_DATA_PATH, self.logger)

    async def run_all(self) -> ReportSummary:
        self.db.initialize()
        started = time.monotonic()
        results: list[CrawlResult] = []
        try:
            for blogger_config in self.bloggers_config["bloggers"]:
                results.append(await self.crawler.crawl_blogger(blogger_config))
        finally:
            await self.crawler.close()
        return self.reporter.generate(results, time.monotonic() - started)

    async def run_one(self, user_id: str) -> ReportSummary:
        self.db.initialize()
        started = time.monotonic()
        target = self._blogger_index.get(str(user_id))
        if target is None:
            raise ValueError(f"Blogger not found in config: {user_id}")

        try:
            results = [await self.crawler.crawl_blogger(target)]
        finally:
            await self.crawler.close()
        return self.reporter.generate(results, time.monotonic() - started)

    async def run_dry_run(self) -> ReportSummary:
        self.db.initialize()
        started = time.monotonic()
        results = [
            CrawlResult(
                blogger_user_id=extract_user_id(item) or str(item.get("homepage_url") or ""),
                status="success",
            )
            for item in self.bloggers_config["bloggers"]
        ]
        await asyncio.sleep(0)
        return self.reporter.generate(results, time.monotonic() - started)
