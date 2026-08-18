import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.tutor import Tutor


def _new_id() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ChatSession(SQLModel, table=True):
    id: str = Field(default_factory=_new_id, primary_key=True)
    tutor_id: str = Field(foreign_key="tutor.id", index=True)
    created_at: datetime = Field(default_factory=_utcnow)
    last_active_at: datetime = Field(default_factory=_utcnow)

    tutor: Optional["Tutor"] = Relationship(back_populates="chat_sessions")
    messages: list["ChatMessage"] = Relationship(
        back_populates="session", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class ChatMessage(SQLModel, table=True):
    # Autoincrement int PK (not exposed via the API) instead of a UUID: it gives a cheap,
    # reliable insertion order for "last N messages" even when two messages share the same
    # wall-clock timestamp (observed on Windows' coarser clock resolution).
    id: int | None = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chatsession.id", index=True)
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=_utcnow)

    session: Optional["ChatSession"] = Relationship(back_populates="messages")
