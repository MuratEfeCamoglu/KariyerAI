from pathlib import Path

from sqlalchemy import text

from app.core.db import create_db_engine


def test_sqlite_engine_creates_parent_dir_and_enables_pragmas(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "test.db"

    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        foreign_keys = conn.execute(text("PRAGMA foreign_keys")).scalar()
    engine.dispose()

    assert db_path.parent.is_dir()
    assert journal_mode == "wal"
    assert foreign_keys == 1
