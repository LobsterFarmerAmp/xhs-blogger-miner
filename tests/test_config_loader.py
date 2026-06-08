import pytest

from src.config_loader import load_bloggers_config, load_settings, validate_bloggers_config


def test_validate_bloggers_config_empty_list_raises() -> None:
    with pytest.raises(ValueError):
        validate_bloggers_config({"bloggers": []})


def test_validate_bloggers_config_missing_bloggers_raises() -> None:
    with pytest.raises(ValueError):
        validate_bloggers_config({})


def test_validate_bloggers_config_each_must_be_dict() -> None:
    with pytest.raises(ValueError):
        validate_bloggers_config({"bloggers": ["not-a-dict"]})


def test_validate_bloggers_config_missing_user_id_and_url_raises() -> None:
    with pytest.raises(ValueError):
        validate_bloggers_config({"bloggers": [{"nickname": "test"}]})


def test_validate_bloggers_config_valid_passes() -> None:
    validate_bloggers_config(
        {
            "bloggers": [
                {"user_id": "5986da286a6a692eaf2a53a1", "nickname": "一起自救"}
            ]
        }
    )


def test_validate_bloggers_config_negative_max_count_raises() -> None:
    with pytest.raises(ValueError):
        validate_bloggers_config(
            {
                "bloggers": [
                    {"user_id": "5986da286a6a692eaf2a53a1", "notes": {"max_count": 0}}
                ]
            }
        )


def test_load_bloggers_config_default_path() -> None:
    config = load_bloggers_config()
    assert isinstance(config.get("bloggers"), list)
    assert len(config["bloggers"]) >= 1
