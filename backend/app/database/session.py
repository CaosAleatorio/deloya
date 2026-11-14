from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def normalize_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


engine = create_engine(normalize_url(get_settings().database_url), pool_pre_ping=True,
                       pool_size=5, max_overflow=5, connect_args={"connect_timeout": 10})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise
