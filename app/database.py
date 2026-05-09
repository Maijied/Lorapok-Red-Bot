from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import Settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def get_engine(settings: Settings):
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url)
    return _engine


def get_session_factory(engine):
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_db(settings: Settings) -> None:
    engine = get_engine(settings)
    Base.metadata.create_all(bind=engine)


def get_db():
    settings = Settings.from_env()
    engine = get_engine(settings)
    SessionLocal = get_session_factory(engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
