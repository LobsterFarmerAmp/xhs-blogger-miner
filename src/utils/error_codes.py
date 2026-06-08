from __future__ import annotations

from enum import IntEnum

from src.mediacrawler import ensure_mediacrawler_path

ensure_mediacrawler_path()


class XHSErrorCode(IntEnum):
    """Known XHS API error codes. Sources: MediaCrawler media_platform/xhs/client.py"""

    CAPTCHA = 471
    IP_BLOCKED = 461
    IP_ERROR = 300012
    NOTE_NOT_FOUND = -510000
    NOTE_ABNORMAL = -510001


def classify_error(exc: Exception) -> XHSErrorCode | None:
    """Try to classify an exception as a known XHS error code."""
    from media_platform.xhs.exception import (
        DataFetchError,
        IPBlockError,
        NoteNotFoundError,
    )

    msg = str(exc)
    if isinstance(exc, IPBlockError):
        return XHSErrorCode.IP_BLOCKED
    if isinstance(exc, NoteNotFoundError):
        if str(XHSErrorCode.NOTE_ABNORMAL.value) in msg:
            return XHSErrorCode.NOTE_ABNORMAL
        return XHSErrorCode.NOTE_NOT_FOUND
    if isinstance(exc, DataFetchError):
        if str(XHSErrorCode.CAPTCHA.value) in msg:
            return XHSErrorCode.CAPTCHA
        if str(XHSErrorCode.IP_BLOCKED.value) in msg:
            return XHSErrorCode.IP_BLOCKED
        if str(XHSErrorCode.IP_ERROR.value) in msg:
            return XHSErrorCode.IP_ERROR
        if str(XHSErrorCode.NOTE_NOT_FOUND.value) in msg:
            return XHSErrorCode.NOTE_NOT_FOUND
        if str(XHSErrorCode.NOTE_ABNORMAL.value) in msg:
            return XHSErrorCode.NOTE_ABNORMAL
    return None


def is_retryable(code: XHSErrorCode | None) -> bool:
    """Return True if the error code suggests retrying with backoff may help."""
    if code is None:
        return False
    return code not in (
        XHSErrorCode.NOTE_NOT_FOUND,
        XHSErrorCode.NOTE_ABNORMAL,
    )
