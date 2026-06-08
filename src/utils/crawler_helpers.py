from __future__ import annotations

import re

RATE_LIMIT_ERROR_MARKERS = ("429", "rate limit", "too many requests", "\u9891\u7e41")
XHS_USER_ID_CHARS = set("0123456789abcdefABCDEF")
_HOMEPAGE_PROFILE_RE = re.compile(r"/profile/([0-9a-fA-F]{24})")


def is_xhs_user_id(value: str) -> bool:
    """Return True if *value* is a valid 24-character XHS user ID (hex string)."""
    return len(value) == 24 and all(char in XHS_USER_ID_CHARS for char in value)


def extract_user_id(item: dict) -> str:
    """Extract user_id from a blogger config item, supporting both user_id key and homepage_url."""
    uid = str(item.get("user_id") or "").strip()
    if is_xhs_user_id(uid):
        return uid
    hp = str(item.get("homepage_url") or "").strip()
    if hp:
        m = _HOMEPAGE_PROFILE_RE.search(hp)
        if m:
            return m.group(1)
    return ""


def is_rate_limit_error(exc: Exception) -> bool:
    """Return True if *exc* messages suggest an HTTP 429 or rate-limiting response."""
    message = str(exc).casefold()
    return any(marker in message for marker in RATE_LIMIT_ERROR_MARKERS)
