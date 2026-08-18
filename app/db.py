from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

if settings.database_url.startswith("sqlite:///"):
    db_path = Path(settings.database_url.removeprefix("sqlite:///"))
    if str(db_path) not in (":memory:",):
        db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    # Import models so they are registered on SQLModel.metadata before create_all.
    from app.models import chat, source, tutor  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
