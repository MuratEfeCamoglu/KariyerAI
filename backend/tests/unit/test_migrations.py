from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core import db as db_module
from app.core.db import create_db_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]


def test_alembic_upgrade_head_on_empty_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_db_engine(f"sqlite:///{(tmp_path / 'migrate.db').as_posix()}")
    # env.py bağlantıyı app.core.db.engine'den alır.
    monkeypatch.setattr(db_module, "engine", engine)

    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")

    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert {"users", "audit_logs"} <= tables
