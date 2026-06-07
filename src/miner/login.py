from __future__ import annotations

import os

from playwright.async_api import BrowserContext, Page

from src.mediacrawler import ensure_mediacrawler_path

ensure_mediacrawler_path()

from media_platform.xhs.login import XiaoHongShuLogin


async def ensure_login(
    context_page: Page,
    browser_context: BrowserContext,
    cookies: str | None = None,
) -> None:
    cookie_str = cookies if cookies is not None else os.getenv("COOKIES", "")
    login_type = "cookie" if cookie_str else "qrcode"

    login = XiaoHongShuLogin(
        login_type=login_type,
        browser_context=browser_context,
        context_page=context_page,
        login_phone="",
        cookie_str=cookie_str,
    )
    await login.begin()
