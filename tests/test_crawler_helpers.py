from src.utils.crawler_helpers import is_rate_limit_error, is_xhs_user_id


def test_is_xhs_user_id_valid() -> None:
    assert is_xhs_user_id("5986da286a6a692eaf2a53a1") is True


def test_is_xhs_user_id_too_short() -> None:
    assert is_xhs_user_id("abc123") is False


def test_is_xhs_user_id_wrong_chars() -> None:
    assert is_xhs_user_id("ffffffffffffffffffffffff") is True  # f is valid hex
    assert is_xhs_user_id("gggggggggggggggggggggggg") is False  # g is not hex


def test_is_rate_limit_error_429() -> None:
    assert is_rate_limit_error(Exception("HTTP 429")) is True


def test_is_rate_limit_error_chinese() -> None:
    assert is_rate_limit_error(Exception("请求频繁")) is True


def test_is_rate_limit_error_rate_limit() -> None:
    assert is_rate_limit_error(Exception("rate limit exceeded")) is True


def test_is_rate_limit_error_normal_error() -> None:
    assert is_rate_limit_error(Exception("connection timeout")) is False
