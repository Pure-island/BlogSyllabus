from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()


def _create_engine() -> Engine:
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

    if settings.database_url.startswith("sqlite:///./"):
        database_path = Path(settings.database_url.replace("sqlite:///./", "", 1))
        database_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(settings.database_url, echo=False, connect_args=connect_args)


engine = _create_engine()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
