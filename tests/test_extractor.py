import json

from src.extractor.blogger import BloggerExtractor
from src.extractor.post import PostExtractor


def test_interaction_count_normalization() -> None:
    normalized = PostExtractor.normalize_count("2.2万")
    assert normalized == {"raw": "2.2万", "value": 22000}


def test_post_extraction_shapes_media_and_tags() -> None:
    post = PostExtractor().extract_post_data(
        {
            "note_id": "note-1",
            "title": "A note",
            "desc": "Body",
            "type": "normal",
            "user": {"user_id": "user-1"},
            "interact_info": {
                "liked_count": "2.2万",
                "collected_count": "12",
                "comment_count": "",
                "share_count": "3",
            },
            "image_list": [{"url_default": "https://example.com/a.jpg"}],
            "tag_list": [{"type": "topic", "name": "topic"}],
        }
    )

    assert post.note_id == "note-1"
    assert post.blogger_user_id == "user-1"
    assert post.liked_count_value == 22000
    assert post.image_urls == ["https://example.com/a.jpg"]
    assert post.tag_list == ["topic"]


def test_post_extraction_preserves_listing_data() -> None:
    post = PostExtractor().extract_post_data(
        {
            "note_id": "note-1",
            "title": "A note",
            "user": {"user_id": "user-1"},
            "listing_data": "from-card",
        },
        listing_data="from-db",
    )

    assert post.listing_data == "from-db"


def test_listing_post_extraction_creates_skeletal_record() -> None:
    note_card = {
        "note_id": "note-1",
        "type": "normal",
        "last_update_time": 123,
        "xsec_token": "token-1",
        "note_card": {"time": 456},
    }

    record = PostExtractor().extract_listing_post(note_card, "user-1")

    assert set(record) == {
        "note_id",
        "blogger_user_id",
        "type",
        "publish_time",
        "last_update_time",
        "note_url",
        "xsec_token",
        "listing_data",
    }
    assert record["publish_time"] == 0
    assert json.loads(record["listing_data"]) == note_card


def test_blogger_extraction_normalizes_counts() -> None:
    blogger = BloggerExtractor().extract_blogger_data(
        {
            "basicInfo": {
                "nickname": "tester",
                "gender": 1,
                "images": "https://example.com/avatar.jpg",
                "desc": "bio",
                "ipLocation": "Shanghai",
            },
            "interactions": [
                {"type": "fans", "count": "1.5万"},
                {"type": "follows", "count": "10"},
                {"type": "interaction", "count": "2.2万"},
            ],
        },
        user_id="user-1",
        homepage_url="https://example.com",
    )

    assert blogger.followers_count == 15000
    assert blogger.following_count == 10
    assert blogger.total_likes == 22000
    assert blogger.gender == "Female"
