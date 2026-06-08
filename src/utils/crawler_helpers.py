from __future__ import annotations

RATE_LIMIT_ERROR_MARKERS = ("429", "rate limit", "too many requests", "\u9891\u7e41")
XHS_USER_ID_CHARS = set("0123456789abcdefABCDEF")


def is_xhs_user_id(value: str) -> bool:
    """Return True if *value* is a valid 24-character XHS user ID (hex string)."""
    return len(value) == 24 and all(char in XHS_USER_ID_CHARS for char in value)


def is_rate_limit_error(exc: Exception) -> bool:
    """Return True if *exc* messages suggest an HTTP 429 or rate-limiting response."""
    message = str(exc).casefold()
    return any(marker in message for marker in RATE_LIMIT_ERROR_MARKERS)
