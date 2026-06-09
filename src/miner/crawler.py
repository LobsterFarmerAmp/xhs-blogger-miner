from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass
from typing import Any

from src.extractor.blogger import BloggerExtractor
from src.extractor.post import PostExtractor
from src.mediacrawler import ensure_mediacrawler_path
from src.miner.human_sim import HumanSimulator
from src.storage.database import Database
from src.storage.models import CrawlLog, utc_now_iso
from src.utils.crawler_helpers import is_xhs_user_id
from src.utils.error_codes import XHSErrorCode, classify_error, is_retryable

ensure_mediacrawler_path()

import config as mediacrawler_config
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.help import parse_creator_info_from_url
from tools.crawler_util import convert_browser_context_cookies

_RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError,
    ConnectionError,
    OSError,
)

try:
    import httpx

    _RETRYABLE_EXCEPTIONS += (httpx.HTTPError,)
except ImportError:
    pass


@dataclass(slots=True)
class CrawlResult:
    blogger_user_id: str
    posts_found: int = 0
    posts_new: int = 0
    status: str = "success"
    error_message: str = ""


@dataclass(frozen=True, slots=True)
class CreatorTarget:
    user_id: str
    xsec_token: str = ""
    xsec_source: str = ""


class BloggerCrawler:
    def __init__(self, config: Any, db: Database, human_sim: HumanSimulator) -> None:
        self.config = config
        self.db = db
        self.human_sim = human_sim
        self.logger = logging.getLogger("xhs_miner.crawler")
        self.blogger_extractor = BloggerExtractor()
        self.post_extractor = PostExtractor()
        self.browser_manager: Any | None = None
        self.browser_context = None
        self.context_page = None
        self.xhs_client: Any | None = None
        self.index_url = "https://www.xiaohongshu.com"
        self.cookie_urls = [self.index_url]

    async def crawl_blogger(
        self,
        blogger_config: dict[str, Any],
        resume: bool = False,
    ) -> CrawlResult:
        started_at = utc_now_iso()
        user_id = self._resolve_user_id(blogger_config)
        collected_note_ids: set[str] = set()
        posts_found = 0
        posts_new = 0
        status = "success"
        error_message = ""

        try:
            if resume:
                last_crawl_log = self.db.get_last_crawl_log(user_id)
                collected_note_ids = self.db.get_collected_note_ids(user_id)
                if collected_note_ids:
                    if last_crawl_log:
                        self.logger.info(
                            "Resuming from crawl log %s: %d posts already "
                            "collected for blogger %s, skipping",
                            last_crawl_log.get("id"),
                            len(collected_note_ids),
                            user_id,
                        )
                    else:
                        self.logger.info(
                            "Resuming: %d posts already collected for blogger "
                            "%s, skipping",
                            len(collected_note_ids),
                            user_id,
                        )
            await self._ensure_client()
            creator_info = await self._get_blogger_info(blogger_config)
            blogger = self.blogger_extractor.extract_blogger_data(
                creator_info or {},
                user_id=user_id,
                homepage_url=str(blogger_config.get("homepage_url") or ""),
                nickname=str(blogger_config.get("nickname") or ""),
            )
            self.db.upsert_blogger(blogger)

            post_cards = await self._get_blogger_posts(
                blogger_config,
                collected_note_ids=collected_note_ids,
            )
            posts_found = len(post_cards)
            if resume:
                posts_found += len(collected_note_ids)

            listing_new = 0
            for post_card in post_cards:
                listing_record = self.post_extractor.extract_listing_post(
                    post_card, user_id
                )
                if self.db.upsert_post(listing_record):
                    listing_new += 1

            self.logger.info(
                "Phase 1 listing complete: found=%d new=%d for blogger %s",
                posts_found,
                listing_new,
                user_id,
            )

            detail_posts = self.db.get_posts_without_detail(user_id)
            self.logger.info(
                "Phase 2 fetch: %d posts need detail for blogger %s",
                len(detail_posts),
                user_id,
            )

            for post_record in detail_posts:
                note_id = str(post_record.get("note_id") or "")
                xsec_token = str(post_record.get("xsec_token") or "")
                listing_data = str(post_record.get("listing_data") or "")

                listing_raw: dict[str, Any] = {}
                try:
                    parsed_listing = json.loads(listing_data or "{}")
                    if isinstance(parsed_listing, dict):
                        listing_raw = parsed_listing
                except (json.JSONDecodeError, TypeError):
                    pass

                try:
                    detail = await self._get_post_detail(
                        note_id,
                        xsec_token=xsec_token,
                        xsec_source=str(listing_raw.get("xsec_source") or "pc_feed"),
                    )
                except Exception as exc:
                    # Unwrap tenacity.RetryError to find root cause
                    root_cause = exc
                    last_attempt = getattr(exc, 'last_attempt', None)
                    if last_attempt is not None:
                        try:
                            inner = last_attempt.exception()
                            if inner is not None:
                                root_cause = inner
                        except Exception:
                            pass
                    err_msg = str(root_cause)
                    self.logger.warning(
                        "Failed to fetch detail for %s: %s",
                        note_id,
                        err_msg[:200],
                    )
                    # 461 CAPTCHA / security verification: stop Phase 2 early
                    if "461" in err_msg or "CAPTCHA" in err_msg.lower():
                        self.logger.warning(
                            "CAPTCHA/461 detected, stopping Phase 2 early. "
                            "Remaining posts will be filled on next --resume."
                        )
                        break
                    # Other errors: skip this post, continue with next
                    continue
                merged = {**listing_raw, **(detail or {})}
                merged.setdefault("xsec_token", xsec_token)
                merged["listing_data"] = listing_data

                full_post = self.post_extractor.extract_post_data(
                    merged,
                    blogger_user_id=user_id,
                    listing_data=listing_data,
                )
                full_post.listing_data = listing_data

                self.db.upsert_post(full_post)
                posts_new += 1
                await self.human_sim.random_delay(
                    self.config.CRAWLER_MIN_SLEEP_SEC,
                    self.config.CRAWLER_MAX_SLEEP_SEC,
                )
        except Exception as exc:
            status = "failed"
            error_message = str(exc)
            self.logger.exception("Failed to crawl blogger %s", user_id)
        finally:
            self.db.insert_crawl_log(
                CrawlLog(
                    blogger_user_id=user_id,
                    started_at=started_at,
                    finished_at=utc_now_iso(),
                    posts_found=posts_found,
                    posts_new=posts_new,
                    status=status,
                    error_message=error_message,
                )
            )

        return CrawlResult(
            blogger_user_id=user_id,
            posts_found=posts_found,
            posts_new=posts_new,
            status=status,
            error_message=error_message,
        )

    async def _get_blogger_info(self, blogger_config: dict[str, Any]) -> dict[str, Any]:
        # Skip HTML scraping (易触发302/重定向/验证), blogger info is non-essential metadata
        creator = self._parse_creator(blogger_config)
        self.logger.info("Skipping creator info HTML fetch for %s", creator.user_id)
        return {}

    async def _get_blogger_posts(
        self,
        blogger_config: dict[str, Any],
        collected_note_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        creator = self._parse_creator(blogger_config)
        max_count = int(
            (blogger_config.get("notes") or {}).get(
                "max_count",
                self.config.CRAWLER_MAX_POSTS_PER_BLOGGER,
            )
        )
        collected_note_ids = collected_note_ids or set()
        notes: list[dict[str, Any]] = []
        posts_seen = 0
        cursor = ""
        has_more = True

        while has_more and posts_seen < max_count:
            page_size = min(30, max_count - posts_seen)
            response = await self._with_retries(
                self.xhs_client.get_notes_by_creator,
                creator=creator.user_id,
                cursor=cursor,
                page_size=page_size,
                xsec_token=creator.xsec_token,
                xsec_source=creator.xsec_source or "pc_feed",
            )
            if not response:
                break
            batch = response.get("notes") or []
            batch = batch[: max_count - posts_seen]
            posts_seen += len(batch)
            new_batch = [
                note
                for note in batch
                if str(note.get("note_id") or note.get("id") or "")
                not in collected_note_ids
            ]
            notes.extend(new_batch)
            has_more = bool(response.get("has_more"))
            # Early-termination: stop when the majority of posts in a batch are
            # before 2024-01-01. Uses note_id first 8 hex chars (Unix timestamp sec).
            # Counts newer-than-cutoff notes: if <50% are new, it's safe to stop.
            if has_more and batch:
                CUTOFF_SEC = 1704038400  # 2024-01-01 00:00:00 CST (Unix seconds)
                newer_count = 0
                total_with_ts = 0
                for n in batch:
                    nid = str(n.get("note_id") or "")
                    if len(nid) >= 8:
                        try:
                            ts = int(nid[:8], 16)
                            total_with_ts += 1
                            if ts >= CUTOFF_SEC:
                                newer_count += 1
                        except (ValueError, TypeError):
                            pass
                if total_with_ts > 0 and newer_count < total_with_ts * 0.5:
                    self.logger.info(
                        "Early-termination: only %d/%d notes >= 2024-01-01 cutoff (%.0f%%)",
                        newer_count,
                        total_with_ts,
                        100 * newer_count / total_with_ts,
                    )
                    has_more = False
            cursor = str(response.get("cursor") or "")
            if has_more:
                await self.human_sim.random_delay(
                    self.config.CRAWLER_MIN_SLEEP_SEC,
                    self.config.CRAWLER_MAX_SLEEP_SEC,
                )

        return notes

    async def _get_post_detail(
        self,
        note_id: str,
        xsec_token: str = "",
        xsec_source: str = "pc_feed",
    ) -> dict[str, Any]:
        if not note_id or self.xhs_client is None:
            return {}
        return await self._with_retries(
            self.xhs_client.get_note_by_id,
            note_id,
            xsec_source,
            xsec_token,
        )

    async def _process_post(self, post_data: dict[str, Any], blogger_user_id: str) -> bool:
        post = self.post_extractor.extract_post_data(post_data, blogger_user_id=blogger_user_id)
        return self.db.upsert_post(post)

    async def _ensure_client(self) -> None:
        if self.xhs_client is not None:
            return

        from src.miner.browser import CDPBrowserManager
        from src.miner.login import ensure_login

        self._apply_mediacrawler_config()
        self.browser_manager = CDPBrowserManager(
            debug_port=int(getattr(self.config, "CDP_DEBUG_PORT", 9222)),
            connect_existing=bool(getattr(self.config, "CDP_CONNECT_EXISTING", False)),
            headless=bool(getattr(self.config, "HEADLESS", True)),
        )
        self.browser_context = await self.browser_manager.create_context()
        self.context_page = await self.browser_context.new_page()
        await self.context_page.goto(self.index_url)
        await self.human_sim.human_page_load(self.context_page)

        self.xhs_client = await self._create_xhs_client()
        if not await self.xhs_client.pong():
            await ensure_login(
                context_page=self.context_page,
                browser_context=self.browser_context,
                cookies=self.config.COOKIES,
            )
            await self.xhs_client.update_cookies(
                browser_context=self.browser_context,
                urls=self.cookie_urls,
            )

    async def _create_xhs_client(self) -> Any:
        cookie_str, cookie_dict = await convert_browser_context_cookies(
            self.browser_context,
            urls=self.cookie_urls,
        )
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json;charset=UTF-8",
            "origin": self.index_url,
            "pragma": "no-cache",
            "referer": f"{self.index_url}/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            ),
            "Cookie": cookie_str,
        }
        return XiaoHongShuClient(
            proxy=None,
            headers=headers,
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
        )

    async def _with_retries(self, func: Any, *args: Any, retries: int = 3, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                return await func(*args, **kwargs)
            except (TypeError, ValueError, AttributeError):
                raise
            except _RETRYABLE_EXCEPTIONS as exc:
                last_error = exc
                error_code = classify_error(exc)
                if error_code is not None and not is_retryable(error_code):
                    self.logger.warning(
                        "Non-retryable error code %s, not retrying",
                        error_code.name,
                    )
                    raise
                if attempt == retries:
                    break
                if error_code is None:
                    sleep_time = min(2 * attempt, self.config.CRAWLER_MAX_SLEEP_SEC)
                elif error_code in (XHSErrorCode.CAPTCHA, XHSErrorCode.IP_BLOCKED):
                    sleep_time = min(
                        4**attempt + random.uniform(1, 5),
                        self.config.CRAWLER_MAX_SLEEP_SEC,
                    )
                elif is_retryable(error_code):
                    sleep_time = min(
                        2**attempt + random.uniform(0, 1),
                        self.config.CRAWLER_MAX_SLEEP_SEC,
                    )
                await asyncio.sleep(sleep_time)
        if last_error is not None:
            raise last_error
        return None

    async def close(self) -> None:
        if self.browser_manager is not None:
            await self.browser_manager.close()
            self.browser_manager = None
            self.xhs_client = None

    def _apply_mediacrawler_config(self) -> None:
        mediacrawler_config.PLATFORM = "xhs"
        mediacrawler_config.CRAWLER_TYPE = self.config.XHS_CRAWLER_TYPE
        mediacrawler_config.COOKIES = self.config.COOKIES
        mediacrawler_config.LOGIN_TYPE = "cookie" if self.config.COOKIES else "qrcode"
        mediacrawler_config.CRAWLER_MAX_NOTES_COUNT = self.config.CRAWLER_MAX_POSTS_PER_BLOGGER
        mediacrawler_config.CRAWLER_MAX_SLEEP_SEC = self.config.CRAWLER_MAX_SLEEP_SEC
        mediacrawler_config.CDP_DEBUG_PORT = int(getattr(self.config, "CDP_DEBUG_PORT", 9222))
        mediacrawler_config.CDP_CONNECT_EXISTING = bool(
            getattr(self.config, "CDP_CONNECT_EXISTING", False)
        )
        mediacrawler_config.CDP_HEADLESS = bool(self.config.HEADLESS)
        mediacrawler_config.HEADLESS = bool(self.config.HEADLESS)
        mediacrawler_config.ENABLE_GET_COMMENTS = False

    def _parse_creator(self, blogger_config: dict[str, Any]) -> CreatorTarget:
        homepage_url = str(blogger_config.get("homepage_url") or "").strip()
        if homepage_url:
            creator = parse_creator_info_from_url(homepage_url)
            return CreatorTarget(
                user_id=creator.user_id,
                xsec_token=creator.xsec_token,
                xsec_source=creator.xsec_source,
            )

        user_id = str(blogger_config.get("user_id") or "").strip()
        if is_xhs_user_id(user_id):
            return CreatorTarget(user_id=user_id)

        raise ValueError(
            "Blogger config must include a non-empty homepage_url or a "
            "24-character hexadecimal user_id"
        )

    def _resolve_user_id(self, blogger_config: dict[str, Any]) -> str:
        return self._parse_creator(blogger_config).user_id
