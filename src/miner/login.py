from __future__ import annotations

import importlib
import logging
import os
import sys

from playwright.async_api import BrowserContext, Page

from src.mediacrawler import ensure_mediacrawler_path

ensure_mediacrawler_path()

from media_platform.xhs.login import XiaoHongShuLogin

_log = logging.getLogger(__name__)


def _patch_media_crawler_tools_utils() -> None:
    """TODO: Long-term fix — push upstream MediaCrawler to fix star imports
    in tools/utils.py. Once fixed, remove this entire function.
    See: proxy/base_proxy.py and tools/async_file_writer.py upstream bugs
    (both had `from tools.utils import utils` instead of `import tools.utils as utils`)."""
    submodule_names = ("tools.crawler_util", "tools.slider_util", "tools.time_util")

    try:
        tools_utils = importlib.import_module("tools.utils")
    except Exception:
        _log.warning("Failed to load MediaCrawler tools.utils for monkey-patch", exc_info=True)
        return

    loaded_submodules = []
    patched_names: set[str] = set()

    for submodule_name in submodule_names:
        try:
            submodule = importlib.import_module(submodule_name)
            loaded_submodules.append(submodule)
            for name in getattr(submodule, "__all__", ()) or ():
                if name.startswith("_"):
                    continue
                try:
                    setattr(tools_utils, name, getattr(submodule, name))
                    patched_names.add(name)
                except Exception:
                    _log.warning(
                        "Failed to patch tools.utils.%s from %s",
                        name,
                        submodule_name,
                        exc_info=True,
                    )
        except Exception:
            _log.warning(
                "Failed to load MediaCrawler utility submodule %s",
                submodule_name,
                exc_info=True,
            )

    if not loaded_submodules:
        raise RuntimeError("Failed to load any MediaCrawler utility submodules")

    # Also pick up any public names that aren't in __all__.
    for submodule_name in submodule_names:
        try:
            submodule = sys.modules.get(submodule_name)
            if submodule is None:
                continue
            for name in dir(submodule):
                if name.startswith("_") or hasattr(tools_utils, name):
                    continue
                try:
                    obj = getattr(submodule, name)
                    if callable(obj) or isinstance(obj, type):
                        setattr(tools_utils, name, obj)
                        patched_names.add(name)
                except Exception:
                    _log.warning(
                        "Failed to patch tools.utils.%s from %s",
                        name,
                        submodule_name,
                        exc_info=True,
                    )
        except Exception:
            _log.warning(
                "Failed while scanning MediaCrawler utility submodule %s",
                submodule_name,
                exc_info=True,
            )

    _log.info("Patched MediaCrawler tools.utils with %s names", len(patched_names))


async def ensure_login(
    context_page: Page,
    browser_context: BrowserContext,
    cookies: str | None = None,
) -> None:
    cookie_str = cookies if cookies is not None else os.getenv("COOKIES", "")
    login_type = "cookie" if cookie_str else "qrcode"

    try:
        _patch_media_crawler_tools_utils()
    except Exception:
        _log.warning(
            "MediaCrawler tools.utils monkey-patch failed; continuing login attempt",
            exc_info=True,
        )

    login = XiaoHongShuLogin(
        login_type=login_type,
        browser_context=browser_context,
        context_page=context_page,
        login_phone="",
        cookie_str=cookie_str,
    )
    await login.begin()
