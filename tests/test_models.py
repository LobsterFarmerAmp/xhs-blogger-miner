from src.storage.database import Database


def test_table_creation() -> None:
    db = Database(":memory:")
    db.initialize()

    with db.connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    table_names = {row["name"] for row in rows}
    assert {"bloggers", "posts", "crawl_logs"}.issubset(table_names)
    db.close()
