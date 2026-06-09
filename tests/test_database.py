from src.storage.database import Database
from src.storage.models import Blogger, CrawlLog, Post, utc_now_iso


def test_database_crud_operations() -> None:
    db = Database(":memory:")
    db.initialize()

    blogger = Blogger(user_id="user-1", nickname="tester")
    db.upsert_blogger(blogger)
    db.upsert_blogger(Blogger(user_id="user-1", nickname="tester-updated"))

    post = Post(
        note_id="note-1",
        blogger_user_id="user-1",
        title="hello",
        image_urls=["https://example.com/a.jpg"],
        tag_list=["tag"],
    )
    assert db.upsert_post(post) is True
    assert db.upsert_post(post) is False

    log_id = db.insert_crawl_log(
        CrawlLog(
            blogger_user_id="user-1",
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            posts_found=1,
            posts_new=1,
            status="success",
        )
    )

    bloggers = db.get_bloggers()
    posts = db.get_posts_for_blogger("user-1")
    assert log_id == 1
    assert bloggers[0]["nickname"] == "tester-updated"
    assert posts[0]["note_id"] == "note-1"
    assert posts[0]["image_urls"] == ["https://example.com/a.jpg"]
    assert posts[0]["listing_data"] == ""
    db.close()


def test_skeletal_posts_are_pending_until_detail_upsert() -> None:
    db = Database(":memory:")
    db.initialize()
    db.upsert_blogger(Blogger(user_id="user-1", nickname="tester"))

    listing_data = '{"note_id": "note-1", "xsec_source": "pc_feed"}'
    assert db.upsert_post(
        {
            "note_id": "note-1",
            "blogger_user_id": "user-1",
            "type": "normal",
            "publish_time": 0,
            "last_update_time": 123,
            "note_url": "https://example.com/note-1",
            "xsec_token": "token-1",
            "listing_data": listing_data,
        }
    ) is True

    pending = db.get_posts_without_detail("user-1")
    assert len(pending) == 1
    assert pending[0]["title"] is None
    assert pending[0]["image_urls"] is None
    assert pending[0]["listing_data"] == listing_data

    assert db.upsert_post(
        Post(
            note_id="note-1",
            blogger_user_id="user-1",
            title="hello",
            listing_data=listing_data,
        )
    ) is False

    assert db.get_posts_without_detail("user-1") == []
    posts = db.get_posts_for_blogger("user-1")
    assert posts[0]["title"] == "hello"
    assert posts[0]["listing_data"] == listing_data
    db.close()
