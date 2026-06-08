from __future__ import annotations

from typing import Any

from playwright.async_api import BrowserContext, Playwright, async_playwright

from src.mediacrawler import ensure_mediacrawler_path

ensure_mediacrawler_path()

import config as mediacrawler_config
from tools.cdp_browser import CDPBrowserManager as MediaCrawlerCDPBrowserManager


class CDPBrowserManager:
    def __init__(
        self,
        debug_port: int = 9222,
        connect_existing: bool = False,
        headless: bool = True,
        user_agent: str | None = None,
    ) -> None:
        self.debug_port = debug_port
        self.connect_existing = connect_existing
        self.headless = headless
        self.user_agent = user_agent
        self._playwright_context: Any = None
        self._playwright: Playwright | None = None
        self._manager: MediaCrawlerCDPBrowserManager | None = None
        self.browser_context: BrowserContext | None = None

    async def create_context(self) -> BrowserContext:
        mediacrawler_config.ENABLE_CDP_MODE = True
        mediacrawler_config.CDP_DEBUG_PORT = self.debug_port
        mediacrawler_config.CDP_CONNECT_EXISTING = self.connect_existing
        mediacrawler_config.CDP_HEADLESS = self.headless
        mediacrawler_config.HEADLESS = self.headless

        self._playwright_context = async_playwright()
        self._playwright = await self._playwright_context.start()
        self._manager = MediaCrawlerCDPBrowserManager()
        self.browser_context = await self._manager.launch_and_connect(
            self._playwright,
            playwright_proxy=None,
            user_agent=self.user_agent,
            headless=self.headless,
        )
        return self.browser_context

    async def close(self) -> None:
        if self._manager is not None:
            await self._manager.cleanup(force=True)
            self._manager = None
        if self._playwright_context is not None:
            await self._playwright_context.__aexit__(None, None, None)
            self._playwright_context = None
            self._playwright = None
