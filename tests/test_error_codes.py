from src.utils.error_codes import XHSErrorCode, classify_error, is_retryable
from media_platform.xhs.exception import DataFetchError, IPBlockError, NoteNotFoundError


def test_classify_ip_block() -> None:
    code = classify_error(IPBlockError("IP blocked"))
    assert code == XHSErrorCode.IP_BLOCKED


def test_classify_note_not_found() -> None:
    code = classify_error(NoteNotFoundError("Note not found"))
    assert code == XHSErrorCode.NOTE_NOT_FOUND


def test_classify_data_fetch_with_code() -> None:
    code = classify_error(DataFetchError("request error, code: 300012"))
    assert code == XHSErrorCode.IP_ERROR


def test_classify_unknown_error() -> None:
    code = classify_error(ValueError("something else"))
    assert code is None


def test_is_retryable_ip_block() -> None:
    assert is_retryable(XHSErrorCode.IP_BLOCKED) is True


def test_is_retryable_note_not_found() -> None:
    assert is_retryable(XHSErrorCode.NOTE_NOT_FOUND) is False


def test_is_retryable_none() -> None:
    assert is_retryable(None) is False
