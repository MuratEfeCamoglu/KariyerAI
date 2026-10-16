from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Dialect, Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import get_settings


class UTCDateTime(TypeDecorator[datetime]):
    """Zamanı UTC saklar ve UTC olarak döner.

    SQLite saat dilimini saklamaz; bu tip olmadan API "2026-10-15T21:08:46" gibi bölgesiz
    zaman döner ve tarayıcı onu yerel saat sanar.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            return value.astimezone(UTC)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


def _enable_sqlite_pragmas(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return create_engine(url)

    # SQLite dosyanın klasörünü kendisi oluşturmaz; temiz bir klonda ilk çalıştırma patlamasın.
    if url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    # BackgroundTasks farklı thread'lerde çalıştığı için aynı bağlantı havuzunu paylaşabilmeli.
    engine = create_engine(url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _enable_sqlite_pragmas)
    return engine


engine = create_db_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def get_session_factory() -> sessionmaker[Session]:
    """Arka plan işleri istek oturumunu kullanamaz (istek bitince kapanır); kendininkini açar."""
    return SessionLocal
