"""Database engine, session factory, and startup migration runner."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

log = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine(database_url: str):
    global _engine
    if _engine is None:
        _engine = create_engine(database_url)
    return _engine


def get_session_factory(engine):
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def run_migrations(database_url: str) -> None:
    """Run ``alembic upgrade head`` programmatically at startup."""
    try:
        from alembic import command  # noqa: I001
        from alembic.config import Config

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        command.upgrade(alembic_cfg, "head")
        log.info("Database migrations applied successfully.")
    except Exception as exc:  # pragma: no cover
        log.warning("Alembic migration failed (falling back to create_all): %s", exc)
        # Fallback: create tables directly — safe for SQLite in tests
        from app.dashboard import models as _models  # noqa: F401

        engine = get_engine(database_url)
        Base.metadata.create_all(bind=engine)


def init_db(database_url: str) -> None:
    """Initialise the database: run migrations then return."""
    run_migrations(database_url)


def get_db(database_url: str):
    """FastAPI dependency — yields a DB session and closes it after the request."""
    engine = get_engine(database_url)
    SessionLocal = get_session_factory(engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
