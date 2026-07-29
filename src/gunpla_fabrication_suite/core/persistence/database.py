"""The database service: engine, session factory, migrations, and integrity checks."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.core.persistence.migrations import run_migrations

_logger = get_logger("database")


def _enable_sqlite_pragmas(dbapi_connection: object, _connection_record: object) -> None:
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


class DatabaseService:
    """Owns the SQLite engine and session factory for the application."""

    def __init__(self, database_file: Path, *, echo: bool = False) -> None:
        self._database_file = database_file
        database_file.parent.mkdir(parents=True, exist_ok=True)

        self._engine: Engine = create_engine(
            f"sqlite:///{database_file}",
            echo=echo,
            connect_args={"check_same_thread": False},
        )
        event.listen(self._engine, "connect", _enable_sqlite_pragmas)

        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @property
    def engine(self) -> Engine:
        """The underlying SQLAlchemy engine."""
        return self._engine

    def migrate(self) -> None:
        """Upgrade the database schema to the latest revision."""
        run_migrations(self._database_file)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a session, committing on success and rolling back on error."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def check_integrity(self) -> bool:
        """Run SQLite's ``PRAGMA integrity_check`` and return whether it passed."""
        with self._engine.connect() as connection:
            result = connection.execute(text("PRAGMA integrity_check")).scalar()
        ok = result == "ok"
        if not ok:
            _logger.error("database_integrity_check_failed", result=result)
        return ok

    def dispose(self) -> None:
        """Dispose of the underlying connection pool."""
        self._engine.dispose()
