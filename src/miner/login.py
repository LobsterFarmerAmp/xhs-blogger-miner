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

    # HACK: tools/utils.py star imports sometimes fail during the full
    # crawler import chain. Force the needed names onto tools.utils so
    # MediaCrawler's login code can find them.
    import importlib
    import sys
    try:
        _tu = importlib.import_module("tools.utils")
        for _submod_name in ("tools.crawler_util", "tools.slider_util", "tools.time_util"):
            try:
                _submod = importlib.import_module(_submod_name)
                for _name in getattr(_submod, "__all__", ()) or ():
                    if not _name.startswith("_"):
                        setattr(_tu, _name, getattr(_submod, _name))
            except Exception:
                pass
        # Also pick up any public names that aren't in __all__
        for _submod_name in ("tools.crawler_util", "tools.slider_util", "tools.time_util"):
            try:
                _submod = sys.modules.get(_submod_name)
                if _submod is None:
                    continue
                for _name in dir(_submod):
                    if _name.startswith("_") or hasattr(_tu, _name):
                        continue
                    obj = getattr(_submod, _name)
                    if callable(obj) or isinstance(obj, type):
                        setattr(_tu, _name, obj)
            except Exception:
                pass
    except Exception:
        pass

    login = XiaoHongShuLogin(
        login_type=login_type,
        browser_context=browser_context,
        context_page=context_page,
        login_phone="",
        cookie_str=cookie_str,
    )
    await login.begin()
